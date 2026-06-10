from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from threading import Lock

from fitmind_agent.core.config import get_settings
from fitmind_agent.db.session import SessionLocal
from fitmind_agent.repositories.memory import ChatSessionSummaryRepository
from fitmind_agent.repositories.memory import ConversationLogRepository
from fitmind_agent.services.llm_service import LLMService
from fitmind_agent.services.prompt_loader import PromptLoader


@dataclass
class SessionCompressionState:
    lock: Lock
    running: bool = False
    dirty: bool = False


class SessionSummaryService:
    _coordinator_lock = Lock()
    _session_states: dict[int, SessionCompressionState] = {}
    _executor: ThreadPoolExecutor | None = None

    def __init__(
        self,
        llm_service: LLMService | None = None,
        prompt_loader: PromptLoader | None = None,
    ) -> None:
        settings = get_settings()
        self.recent_context_rounds = settings.recent_context_rounds
        self.llm_service = llm_service or LLMService()
        self.prompt_loader = prompt_loader or PromptLoader()

        if SessionSummaryService._executor is None:
            SessionSummaryService._executor = ThreadPoolExecutor(
                max_workers=settings.summary_compression_workers,
                thread_name_prefix="fitmind-summary",
            )

    def schedule_session_compression(self, session_id: int) -> None:
        with self._coordinator_lock:
            state = self._session_states.setdefault(session_id, SessionCompressionState(lock=Lock()))
            state.dirty = True
            if state.running:
                return
            state.running = True

        assert self._executor is not None
        self._executor.submit(self._run_compression_loop, session_id)

    def _run_compression_loop(self, session_id: int) -> None:
        state = self._session_states[session_id]
        with state.lock:
            while True:
                with self._coordinator_lock:
                    state.dirty = False

                self._compress_session_once(session_id)

                with self._coordinator_lock:
                    if state.dirty:
                        continue
                    state.running = False
                    break

    def _compress_session_once(self, session_id: int) -> bool:
        session = SessionLocal()
        try:
            log_repo = ConversationLogRepository(session)
            summary_repo = ChatSessionSummaryRepository(session)

            latest_summary = summary_repo.get_latest_by_session_and_type(
                session_id=session_id,
                summary_type="running_summary",
            )
            summary_text = latest_summary.summary_text if latest_summary else ""
            summary_payload = (latest_summary.structured_payload or {}) if latest_summary else {}
            compressed_until_log_id = (
                summary_payload.get("compressed_until_log_id", 0) if isinstance(summary_payload, dict) else 0
            )

            recent_logs = log_repo.list_recent_by_session(
                session_id=session_id,
                limit=self.recent_context_rounds * 2 + 1,
            )
            if len(recent_logs) <= self.recent_context_rounds * 2:
                return False

            active_window_first_log_id = recent_logs[-(self.recent_context_rounds * 2)].id
            compressible_logs = log_repo.list_between_session_watermarks(
                session_id=session_id,
                after_log_id=compressed_until_log_id or None,
                before_log_id=active_window_first_log_id,
            )
            if not compressible_logs:
                return False

            transcript = self._format_transcript(compressible_logs)
            system_prompt = self.prompt_loader.load("session_summary/system.txt")
            user_prompt = self.prompt_loader.render(
                "session_summary/user.txt",
                previous_summary=summary_text or "暂无历史摘要。",
                transcript=transcript,
            )
            new_summary = self.llm_service.generate_text(
                user_text=user_prompt,
                system_prompt=system_prompt,
            )

            new_version = 1 if latest_summary is None else latest_summary.summary_version + 1
            last_log_id = compressible_logs[-1].id
            total_compressed_count = len(compressible_logs)
            previous_count = latest_summary.source_message_count if latest_summary else 0

            summary_repo.create(
                {
                    "session_id": session_id,
                    "user_id": compressible_logs[-1].user_id,
                    "summary_type": "running_summary",
                    "summary_text": new_summary,
                    "structured_payload": {
                        "compressed_until_log_id": last_log_id,
                        "compressed_from_log_id": compressible_logs[0].id,
                        "window_round_limit": self.recent_context_rounds,
                    },
                    "summary_version": new_version,
                    "source_message_count": previous_count + total_compressed_count,
                }
            )
            return True
        finally:
            session.close()

    @staticmethod
    def _format_transcript(logs) -> str:
        lines: list[str] = []
        for log in logs:
            lines.append(f"{log.role}: {log.message_text}")
        return "\n".join(lines)
