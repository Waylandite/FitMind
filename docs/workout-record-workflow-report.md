# 训练记录提取与确认落库流程报告

测试日期：2026-06-13

## 目标

当用户输入被识别为 `today_workout_record` 后，FitMind 不直接写入正式训练表，而是先提取结构化训练记录 JSON，邀请用户确认或修正。用户确认后，再写入正式训练记录表。

## 本次实现

新增核心组件：

- `workout_record_drafts`
  保存待确认训练记录草稿。
- `WorkoutRecordService`
  管理“提取、修正、确认、取消、正式落库”的流程。
- `WorkoutRecordDraftRepository`
  管理训练记录草稿。
- `WorkoutRecordRepository`
  管理正式训练主记录和动作明细。
- `workout_record_extraction` prompt
  统一存放在 `agent/src/fitmind_agent/prompts/workout_record_extraction`。

## 流程设计

1. 用户输入训练记录，例如“今天练胸，卧推 5 组 80kg”。
2. 意图识别为 `today_workout_record`。
3. LLM 根据提取 prompt 输出结构化 JSON。
4. 系统写入 `workout_record_drafts`，状态为 `pending`。
5. 系统回复用户确认文本。
6. 用户可以回复：
   - `确认保存`：写入正式表。
   - `取消`：取消草稿。
   - 修正内容：更新同一条 pending draft。
   - 提问：解释当前草稿，不写正式表。
7. 确认后写入：
   - `user_workout_records`
   - `user_workout_record_items`
8. draft 状态更新为 `confirmed`，并关联正式 `workout_record_id`。

## 结构化 JSON 示例

```json
{
  "record_date": "2026-06-13",
  "session_name": "胸部训练",
  "duration_minutes": null,
  "completion_status": "completed",
  "perceived_exertion": null,
  "energy_level": null,
  "mood": null,
  "exercises": [
    {
      "exercise_name": "卧推",
      "sets_count": 5,
      "reps_text": null,
      "weight_text": "80kg",
      "duration_text": null,
      "distance_text": null,
      "raw_text": "卧推 5 组 80kg",
      "remark": null
    }
  ],
  "confidence": 0.86,
  "missing_fields": ["次数"],
  "summary_text": "已提取 1 个动作：卧推 5 组，重量 80kg。"
}
```

## 已完成验证

- `python3 -m compileall agent/src` 通过。
- `npm run build` 通过。
- Alembic 迁移已执行成功，`workout_record_drafts` 已创建到本地 MySQL。

## 联调状态

本轮尝试通过本地 HTTP 调用 `/api/v1/chat/stream` 做端到端测试时，工具审批额度触发限制，无法继续执行真实本地接口联调。

因此当前状态是：

- 代码编译通过。
- 数据库迁移通过。
- 前端构建通过。
- 真实 HTTP 端到端确认保存流程仍需下一轮在工具可用时执行。

建议下一轮优先测试：

1. 发送训练记录文本，确认返回 `workflow.action=draft_created`。
2. 检查 `workout_record_drafts.status=pending`。
3. 回复“确认保存”。
4. 检查 `user_workout_records` 和 `user_workout_record_items` 是否写入。
5. 检查 draft 状态是否变为 `confirmed`。
