-- MySQL dump 10.13  Distrib 8.4.6, for macos15 (arm64)
--
-- Host: 127.0.0.1    Database: fitmind
-- ------------------------------------------------------
-- Server version	8.4.6

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `fitmind`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `fitmind` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `fitmind`;

--
-- Table structure for table `agent_derived_memories`
--

DROP TABLE IF EXISTS `agent_derived_memories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `agent_derived_memories` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `memory_category` varchar(60) NOT NULL,
  `memory_type` varchar(100) NOT NULL,
  `summary_text` text NOT NULL,
  `structured_payload` json DEFAULT NULL,
  `confidence_score` decimal(4,3) DEFAULT NULL,
  `source_session_id` bigint DEFAULT NULL,
  `source_conversation_log_id` bigint DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `valid_from` date DEFAULT NULL,
  `valid_to` date DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `fk_agent_derived_memories_source_conversation_log_id` (`source_conversation_log_id`),
  KEY `idx_agent_derived_memories_user_category_status` (`user_id`,`memory_category`,`status`),
  KEY `idx_agent_derived_memories_user_type_status` (`user_id`,`memory_type`,`status`),
  KEY `idx_agent_derived_memories_source_session_id` (`source_session_id`),
  CONSTRAINT `fk_agent_derived_memories_source_conversation_log_id` FOREIGN KEY (`source_conversation_log_id`) REFERENCES `conversation_logs` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_agent_derived_memories_source_session_id` FOREIGN KEY (`source_session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_agent_derived_memories_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_agent_derived_memories_category` CHECK ((`memory_category` in (_utf8mb4'fitness_goal_memory',_utf8mb4'training_pattern_memory',_utf8mb4'exercise_preference_memory',_utf8mb4'body_status_baseline_memory',_utf8mb4'nutrition_pattern_memory',_utf8mb4'conversation_style_memory',_utf8mb4'current_phase_memory',_utf8mb4'adherence_risk_memory'))),
  CONSTRAINT `chk_agent_derived_memories_confidence` CHECK (((`confidence_score` is null) or ((`confidence_score` >= 0) and (`confidence_score` <= 1)))),
  CONSTRAINT `chk_agent_derived_memories_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'superseded',_utf8mb4'expired')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `alembic_version`
--

DROP TABLE IF EXISTS `alembic_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `alembic_version` (
  `version_num` varchar(32) NOT NULL,
  PRIMARY KEY (`version_num`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `auth_refresh_sessions`
--

DROP TABLE IF EXISTS `auth_refresh_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `auth_refresh_sessions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `token_hash` varchar(64) NOT NULL,
  `family_id` varchar(36) NOT NULL,
  `expires_at` datetime NOT NULL,
  `last_used_at` datetime DEFAULT NULL,
  `revoked_at` datetime DEFAULT NULL,
  `replaced_by_id` bigint DEFAULT NULL,
  `user_agent` varchar(512) DEFAULT NULL,
  `ip_address` varchar(64) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_auth_refresh_sessions_token_hash` (`token_hash`),
  KEY `replaced_by_id` (`replaced_by_id`),
  KEY `ix_auth_refresh_sessions_user_id` (`user_id`),
  KEY `ix_auth_refresh_sessions_family_id` (`family_id`),
  KEY `ix_auth_refresh_sessions_expires_at` (`expires_at`),
  KEY `ix_auth_refresh_sessions_revoked_at` (`revoked_at`),
  CONSTRAINT `auth_refresh_sessions_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `auth_refresh_sessions_ibfk_2` FOREIGN KEY (`replaced_by_id`) REFERENCES `auth_refresh_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `body_status_record_drafts`
--

DROP TABLE IF EXISTS `body_status_record_drafts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `body_status_record_drafts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` bigint DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `raw_text` text NOT NULL,
  `draft_payload` json DEFAULT NULL,
  `confidence_score` decimal(4,3) DEFAULT NULL,
  `confirmed_at` datetime DEFAULT NULL,
  `body_status_record_id` bigint DEFAULT NULL,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `body_status_record_id` (`body_status_record_id`),
  KEY `idx_body_status_record_drafts_session_status` (`session_id`,`status`,`id`),
  KEY `idx_body_status_record_drafts_user_status` (`user_id`,`status`,`id`),
  CONSTRAINT `body_status_record_drafts_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `body_status_record_drafts_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `body_status_record_drafts_ibfk_3` FOREIGN KEY (`body_status_record_id`) REFERENCES `user_body_status_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_body_status_record_drafts_confidence` CHECK (((`confidence_score` is null) or ((`confidence_score` >= 0) and (`confidence_score` <= 1)))),
  CONSTRAINT `chk_body_status_record_drafts_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'confirmed',_utf8mb4'cancelled',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chat_session_summaries`
--

DROP TABLE IF EXISTS `chat_session_summaries`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_session_summaries` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `session_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `summary_type` varchar(30) NOT NULL,
  `summary_text` text NOT NULL,
  `structured_payload` json DEFAULT NULL,
  `summary_version` int NOT NULL DEFAULT '1',
  `source_message_count` int DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chat_session_summaries_version` (`session_id`,`summary_type`,`summary_version`),
  KEY `fk_chat_session_summaries_user_id` (`user_id`),
  KEY `idx_chat_session_summaries_session_type_version` (`session_id`,`summary_type`,`summary_version`),
  CONSTRAINT `fk_chat_session_summaries_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_chat_session_summaries_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_chat_session_summaries_type` CHECK ((`summary_type` in (_utf8mb4'running_summary',_utf8mb4'final_summary',_utf8mb4'memory_candidate')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chat_sessions`
--

DROP TABLE IF EXISTS `chat_sessions`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_sessions` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `thread_id` varchar(100) NOT NULL,
  `session_no` int NOT NULL DEFAULT '1',
  `title` varchar(255) DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `started_at` datetime NOT NULL DEFAULT (now()),
  `ended_at` datetime DEFAULT NULL,
  `last_message_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chat_sessions_user_thread_no` (`user_id`,`thread_id`,`session_no`),
  KEY `idx_chat_sessions_user_status_last_message_at` (`user_id`,`status`,`last_message_at`),
  CONSTRAINT `fk_chat_sessions_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_chat_sessions_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'closed',_utf8mb4'archived')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `chat_turn_token_usage`
--

DROP TABLE IF EXISTS `chat_turn_token_usage`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `chat_turn_token_usage` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `request_id` varchar(64) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  `thread_id` varchar(100) DEFAULT NULL,
  `session_id` bigint DEFAULT NULL,
  `intent_type` varchar(80) DEFAULT NULL,
  `total_prompt_tokens` int NOT NULL DEFAULT '0',
  `total_completion_tokens` int NOT NULL DEFAULT '0',
  `total_tokens` int NOT NULL DEFAULT '0',
  `llm_call_count` int NOT NULL DEFAULT '0',
  `model_breakdown` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_chat_turn_token_usage_request_id` (`request_id`),
  KEY `idx_chat_turn_token_usage_session` (`session_id`,`created_at`),
  KEY `idx_chat_turn_token_usage_user_created` (`user_id`,`created_at`),
  CONSTRAINT `chat_turn_token_usage_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chat_turn_token_usage_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `conversation_logs`
--

DROP TABLE IF EXISTS `conversation_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `conversation_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `thread_id` varchar(100) NOT NULL,
  `record_date` date DEFAULT NULL,
  `role` varchar(20) NOT NULL,
  `message_text` text NOT NULL,
  `intent_type` varchar(30) DEFAULT NULL,
  `related_plan_id` bigint DEFAULT NULL,
  `related_workout_record_id` bigint DEFAULT NULL,
  `related_nutrition_record_id` bigint DEFAULT NULL,
  `related_body_status_record_id` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `session_id` bigint DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `fk_conversation_logs_related_plan_id` (`related_plan_id`),
  KEY `fk_conversation_logs_related_workout_record_id` (`related_workout_record_id`),
  KEY `fk_conversation_logs_related_nutrition_record_id` (`related_nutrition_record_id`),
  KEY `fk_conversation_logs_related_body_status_record_id` (`related_body_status_record_id`),
  KEY `idx_conversation_logs_user_record_date` (`user_id`,`record_date`),
  KEY `idx_conversation_logs_thread_created_at` (`thread_id`,`created_at`),
  KEY `idx_conversation_logs_session_created_at` (`session_id`,`created_at`),
  CONSTRAINT `fk_conversation_logs_related_body_status_record_id` FOREIGN KEY (`related_body_status_record_id`) REFERENCES `user_body_status_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_logs_related_nutrition_record_id` FOREIGN KEY (`related_nutrition_record_id`) REFERENCES `user_nutrition_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_logs_related_plan_id` FOREIGN KEY (`related_plan_id`) REFERENCES `user_workout_plans` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_logs_related_workout_record_id` FOREIGN KEY (`related_workout_record_id`) REFERENCES `user_workout_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_logs_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_conversation_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_conversation_logs_intent_type` CHECK (((`intent_type` is null) or (`intent_type` in (_utf8mb4'plan',_utf8mb4'workout',_utf8mb4'nutrition',_utf8mb4'body_status',_utf8mb4'correction',_utf8mb4'query')))),
  CONSTRAINT `chk_conversation_logs_role` CHECK ((`role` in (_utf8mb4'user',_utf8mb4'assistant',_utf8mb4'system')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `intent_clarifications`
--

DROP TABLE IF EXISTS `intent_clarifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `intent_clarifications` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` bigint NOT NULL,
  `original_query` text NOT NULL,
  `candidate_intents` json NOT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `active_session_key` bigint DEFAULT NULL,
  `attempt_count` int NOT NULL DEFAULT '1',
  `max_attempts` int NOT NULL DEFAULT '2',
  `last_question` text NOT NULL,
  `last_user_reply` text,
  `resolved_intent` varchar(80) DEFAULT NULL,
  `resolved_confidence` decimal(4,3) DEFAULT NULL,
  `resolution_source` varchar(30) DEFAULT NULL,
  `expires_at` datetime NOT NULL,
  `resolved_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `active_session_key` (`active_session_key`),
  KEY `session_id` (`session_id`),
  KEY `idx_intent_clarifications_active` (`user_id`,`session_id`,`status`),
  CONSTRAINT `intent_clarifications_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `intent_clarifications_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_intent_clarifications_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'resolved',_utf8mb4'cancelled',_utf8mb4'expired',_utf8mb4'failed',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `intent_recognition_logs`
--

DROP TABLE IF EXISTS `intent_recognition_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `intent_recognition_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `thread_id` varchar(100) NOT NULL,
  `session_id` bigint DEFAULT NULL,
  `message_text` text NOT NULL,
  `final_intent` varchar(80) NOT NULL,
  `confidence_score` decimal(4,3) NOT NULL,
  `source` varchar(20) NOT NULL,
  `reason` text,
  `keyword_intent` varchar(80) DEFAULT NULL,
  `keyword_confidence` decimal(4,3) DEFAULT NULL,
  `matched_keywords` json DEFAULT NULL,
  `module_name` varchar(100) DEFAULT NULL,
  `module_status` varchar(30) DEFAULT NULL,
  `db_intent_type` varchar(30) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `idx_intent_recognition_logs_user_created` (`user_id`,`created_at`),
  KEY `idx_intent_recognition_logs_session` (`session_id`,`id`),
  KEY `idx_intent_recognition_logs_final_intent` (`final_intent`,`created_at`),
  CONSTRAINT `fk_intent_recognition_logs_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_intent_recognition_logs_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_intent_recognition_logs_confidence` CHECK (((`confidence_score` >= 0) and (`confidence_score` <= 1))),
  CONSTRAINT `chk_intent_recognition_logs_source` CHECK ((`source` in (_utf8mb4'llm',_utf8mb4'keyword',_utf8mb4'fallback')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `llm_call_logs`
--

DROP TABLE IF EXISTS `llm_call_logs`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `llm_call_logs` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `request_id` varchar(64) NOT NULL,
  `user_id` bigint DEFAULT NULL,
  `thread_id` varchar(100) DEFAULT NULL,
  `session_id` bigint DEFAULT NULL,
  `workflow` varchar(80) DEFAULT NULL,
  `node_name` varchar(100) DEFAULT NULL,
  `provider` varchar(50) NOT NULL DEFAULT 'deepseek',
  `model` varchar(100) NOT NULL,
  `is_stream` tinyint(1) NOT NULL DEFAULT '0',
  `prompt_tokens` int DEFAULT NULL,
  `completion_tokens` int DEFAULT NULL,
  `total_tokens` int DEFAULT NULL,
  `reasoning_tokens` int DEFAULT NULL,
  `cached_tokens` int DEFAULT NULL,
  `usage_source` varchar(30) NOT NULL DEFAULT 'provider',
  `latency_ms` int DEFAULT NULL,
  `success` tinyint(1) NOT NULL DEFAULT '1',
  `error_message` text,
  `raw_usage` json DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `idx_llm_call_logs_request` (`request_id`,`id`),
  KEY `idx_llm_call_logs_session` (`session_id`,`created_at`),
  KEY `idx_llm_call_logs_user_created` (`user_id`,`created_at`),
  KEY `idx_llm_call_logs_model_created` (`model`,`created_at`),
  CONSTRAINT `llm_call_logs_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE SET NULL,
  CONSTRAINT `llm_call_logs_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_llm_call_logs_usage_source` CHECK ((`usage_source` in (_utf8mb4'provider',_utf8mb4'estimated',_utf8mb4'unavailable')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `nutrition_record_drafts`
--

DROP TABLE IF EXISTS `nutrition_record_drafts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `nutrition_record_drafts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` bigint DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `raw_text` text NOT NULL,
  `draft_payload` json DEFAULT NULL,
  `confidence_score` decimal(4,3) DEFAULT NULL,
  `confirmed_at` datetime DEFAULT NULL,
  `nutrition_record_id` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `fk_nutrition_record_drafts_nutrition_record_id` (`nutrition_record_id`),
  KEY `idx_nutrition_record_drafts_session_status` (`session_id`,`status`,`id`),
  KEY `idx_nutrition_record_drafts_user_status` (`user_id`,`status`,`id`),
  CONSTRAINT `fk_nutrition_record_drafts_nutrition_record_id` FOREIGN KEY (`nutrition_record_id`) REFERENCES `user_nutrition_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_nutrition_record_drafts_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_nutrition_record_drafts_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_nutrition_record_drafts_confidence` CHECK (((`confidence_score` is null) or ((`confidence_score` >= 0) and (`confidence_score` <= 1)))),
  CONSTRAINT `chk_nutrition_record_drafts_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'confirmed',_utf8mb4'cancelled',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_body_status_records`
--

DROP TABLE IF EXISTS `user_body_status_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_body_status_records` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `record_date` date NOT NULL,
  `sleep_hours` decimal(4,2) DEFAULT NULL,
  `fatigue_level` smallint DEFAULT NULL,
  `stress_level` smallint DEFAULT NULL,
  `soreness_level` smallint DEFAULT NULL,
  `body_weight_kg` decimal(6,2) DEFAULT NULL,
  `mood` varchar(50) DEFAULT NULL,
  `raw_text` text NOT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_body_status_records_user_date` (`user_id`,`record_date`),
  CONSTRAINT `fk_user_body_status_records_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_body_status_records_fatigue_level` CHECK (((`fatigue_level` is null) or (`fatigue_level` between 1 and 10))),
  CONSTRAINT `chk_user_body_status_records_soreness_level` CHECK (((`soreness_level` is null) or (`soreness_level` between 1 and 10))),
  CONSTRAINT `chk_user_body_status_records_stress_level` CHECK (((`stress_level` is null) or (`stress_level` between 1 and 10)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_defined_memories`
--

DROP TABLE IF EXISTS `user_defined_memories`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_defined_memories` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `memory_key` varchar(100) NOT NULL,
  `memory_category` varchar(50) NOT NULL,
  `memory_value` text,
  `raw_text` text,
  `priority` smallint NOT NULL DEFAULT '100',
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `source_conversation_log_id` bigint DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `fk_user_defined_memories_source_conversation_log_id` (`source_conversation_log_id`),
  KEY `idx_user_defined_memories_user_category_status` (`user_id`,`memory_category`,`status`),
  KEY `idx_user_defined_memories_user_key_status` (`user_id`,`memory_key`,`status`),
  CONSTRAINT `fk_user_defined_memories_source_conversation_log_id` FOREIGN KEY (`source_conversation_log_id`) REFERENCES `conversation_logs` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_defined_memories_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_defined_memories_category` CHECK ((`memory_category` in (_utf8mb4'fitness_preference',_utf8mb4'content_preference',_utf8mb4'conversation_preference',_utf8mb4'diet_preference',_utf8mb4'health_constraint_preference'))),
  CONSTRAINT `chk_user_defined_memories_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'archived')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_nutrition_records`
--

DROP TABLE IF EXISTS `user_nutrition_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_nutrition_records` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `record_date` date NOT NULL,
  `raw_text` text NOT NULL,
  `calories_estimate` decimal(8,2) DEFAULT NULL,
  `protein_g_estimate` decimal(8,2) DEFAULT NULL,
  `carbs_g_estimate` decimal(8,2) DEFAULT NULL,
  `fat_g_estimate` decimal(8,2) DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_nutrition_records_user_date` (`user_id`,`record_date`),
  CONSTRAINT `fk_user_nutrition_records_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_profiles`
--

DROP TABLE IF EXISTS `user_profiles`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_profiles` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `gender` varchar(20) DEFAULT NULL,
  `birth_date` date DEFAULT NULL,
  `height_cm` decimal(5,2) DEFAULT NULL,
  `weight_kg` decimal(6,2) DEFAULT NULL,
  `target_weight_kg` decimal(6,2) DEFAULT NULL,
  `goal_type` varchar(50) DEFAULT NULL,
  `training_level` varchar(50) DEFAULT NULL,
  `injury_notes` text,
  `medical_notes` text,
  `diet_preference` text,
  `preferred_training_days` text,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_user_profiles_user_id` (`user_id`),
  CONSTRAINT `fk_user_profiles_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_workout_plans`
--

DROP TABLE IF EXISTS `user_workout_plans`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_workout_plans` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `title` varchar(255) DEFAULT NULL,
  `plan_date` date DEFAULT NULL,
  `raw_text` text NOT NULL,
  `source` varchar(20) NOT NULL DEFAULT 'manual',
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `idx_user_workout_plans_user_date` (`user_id`,`plan_date`),
  CONSTRAINT `fk_user_workout_plans_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_workout_plans_source` CHECK ((`source` in (_utf8mb4'manual',_utf8mb4'agent'))),
  CONSTRAINT `chk_user_workout_plans_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'archived')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_workout_record_items`
--

DROP TABLE IF EXISTS `user_workout_record_items`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_workout_record_items` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `workout_record_id` bigint NOT NULL,
  `sequence_no` int NOT NULL DEFAULT '1',
  `exercise_name` varchar(255) NOT NULL,
  `sets_count` int DEFAULT NULL,
  `reps_text` varchar(100) DEFAULT NULL,
  `weight_text` varchar(100) DEFAULT NULL,
  `duration_text` varchar(100) DEFAULT NULL,
  `distance_text` varchar(100) DEFAULT NULL,
  `raw_text` text,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  `exercise_type` varchar(20) NOT NULL DEFAULT 'strength',
  PRIMARY KEY (`id`),
  KEY `idx_user_workout_record_items_record_sequence` (`workout_record_id`,`sequence_no`),
  KEY `idx_user_workout_record_items_type` (`exercise_type`,`workout_record_id`),
  CONSTRAINT `fk_user_workout_record_items_record_id` FOREIGN KEY (`workout_record_id`) REFERENCES `user_workout_records` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_workout_record_items_exercise_type` CHECK ((`exercise_type` in (_utf8mb4'strength',_utf8mb4'cardio',_utf8mb4'mobility',_utf8mb4'other')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `user_workout_records`
--

DROP TABLE IF EXISTS `user_workout_records`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_workout_records` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `record_date` date NOT NULL,
  `plan_id` bigint DEFAULT NULL,
  `session_name` varchar(255) DEFAULT NULL,
  `duration_minutes` int DEFAULT NULL,
  `completion_status` varchar(20) NOT NULL DEFAULT 'completed',
  `perceived_exertion` smallint DEFAULT NULL,
  `energy_level` smallint DEFAULT NULL,
  `mood` varchar(50) DEFAULT NULL,
  `raw_text` text NOT NULL,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `idx_user_workout_records_plan_id` (`plan_id`),
  KEY `idx_user_workout_records_user_id` (`user_id`),
  KEY `idx_user_workout_records_user_date` (`user_id`,`record_date`,`id`),
  CONSTRAINT `fk_user_workout_records_plan_id` FOREIGN KEY (`plan_id`) REFERENCES `user_workout_plans` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_user_workout_records_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `chk_user_workout_records_completion_status` CHECK ((`completion_status` in (_utf8mb4'completed',_utf8mb4'partial',_utf8mb4'skipped'))),
  CONSTRAINT `chk_user_workout_records_energy_level` CHECK (((`energy_level` is null) or (`energy_level` between 1 and 10))),
  CONSTRAINT `chk_user_workout_records_perceived_exertion` CHECK (((`perceived_exertion` is null) or (`perceived_exertion` between 1 and 10)))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `email` varchar(255) NOT NULL,
  `username` varchar(100) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `display_name` varchar(100) DEFAULT NULL,
  `avatar_url` text,
  `status` varchar(20) NOT NULL DEFAULT 'active',
  `last_login_at` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  `auth_version` int NOT NULL DEFAULT '1',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uq_users_email` (`email`),
  UNIQUE KEY `uq_users_username` (`username`),
  CONSTRAINT `chk_users_status` CHECK ((`status` in (_utf8mb4'active',_utf8mb4'disabled',_utf8mb4'deleted')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_plan_drafts`
--

DROP TABLE IF EXISTS `workout_plan_drafts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_plan_drafts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` bigint DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `raw_text` text NOT NULL,
  `draft_payload` json DEFAULT NULL,
  `confidence_score` decimal(4,3) DEFAULT NULL,
  `confirmed_at` datetime DEFAULT NULL,
  `workout_plan_id` bigint DEFAULT NULL,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `workout_plan_id` (`workout_plan_id`),
  KEY `idx_workout_plan_drafts_session_status` (`session_id`,`status`,`id`),
  KEY `idx_workout_plan_drafts_user_status` (`user_id`,`status`,`id`),
  CONSTRAINT `workout_plan_drafts_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `workout_plan_drafts_ibfk_2` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `workout_plan_drafts_ibfk_3` FOREIGN KEY (`workout_plan_id`) REFERENCES `user_workout_plans` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_workout_plan_drafts_confidence` CHECK (((`confidence_score` is null) or ((`confidence_score` >= 0) and (`confidence_score` <= 1)))),
  CONSTRAINT `chk_workout_plan_drafts_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'confirmed',_utf8mb4'cancelled',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `workout_record_drafts`
--

DROP TABLE IF EXISTS `workout_record_drafts`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `workout_record_drafts` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `user_id` bigint NOT NULL,
  `session_id` bigint DEFAULT NULL,
  `status` varchar(20) NOT NULL DEFAULT 'pending',
  `raw_text` text NOT NULL,
  `draft_payload` json DEFAULT NULL,
  `confidence_score` decimal(4,3) DEFAULT NULL,
  `confirmed_at` datetime DEFAULT NULL,
  `workout_record_id` bigint DEFAULT NULL,
  `remark` text,
  `created_at` datetime NOT NULL DEFAULT (now()),
  `updated_at` datetime NOT NULL DEFAULT (now()),
  PRIMARY KEY (`id`),
  KEY `fk_workout_record_drafts_workout_record_id` (`workout_record_id`),
  KEY `idx_workout_record_drafts_session_status` (`session_id`,`status`,`id`),
  KEY `idx_workout_record_drafts_user_status` (`user_id`,`status`,`id`),
  CONSTRAINT `fk_workout_record_drafts_session_id` FOREIGN KEY (`session_id`) REFERENCES `chat_sessions` (`id`) ON DELETE SET NULL,
  CONSTRAINT `fk_workout_record_drafts_user_id` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE,
  CONSTRAINT `fk_workout_record_drafts_workout_record_id` FOREIGN KEY (`workout_record_id`) REFERENCES `user_workout_records` (`id`) ON DELETE SET NULL,
  CONSTRAINT `chk_workout_record_drafts_confidence` CHECK (((`confidence_score` is null) or ((`confidence_score` >= 0) and (`confidence_score` <= 1)))),
  CONSTRAINT `chk_workout_record_drafts_status` CHECK ((`status` in (_utf8mb4'pending',_utf8mb4'confirmed',_utf8mb4'cancelled',_utf8mb4'superseded')))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping events for database 'fitmind'
--

--
-- Dumping routines for database 'fitmind'
--
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-10-30  0:22:54
