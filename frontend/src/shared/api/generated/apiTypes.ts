// GENERATED FILE. DO NOT EDIT.
// Source: backend DRF/drf-spectacular OpenAPI schema.
// Regenerate with: python scripts/generate_api_contract.py

export type JsonPrimitive = string | number | boolean | null
export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]
export type JsonObject = { [key: string]: JsonValue }

export type ApiSchemas = {
  "AccessTokenResponse": { "access": string }
  "ActionEnum": "grant_coins" | "set_staff" | "set_active"
  "AdminAnalyticsResponse": { "active_learners_30d": number; "completions": ApiSchemas["AdminCompletions"]; "per_story": Array<ApiSchemas["AdminStoryAnalytics"]>; "runs": ApiSchemas["AdminRuns"] }
  "AdminChapter": { "battle_stage": { [key: string]: JsonValue }; "description": string; "id": number; "is_playable": boolean; "is_published": boolean; "management_source": string; "number": number; "slug": string; "sort_order": number; "story_id": number | null; "title": string }
  "AdminChapterCreateRequest": { "battle_stage"?: { [key: string]: JsonValue }; "description"?: string; "is_playable"?: boolean; "is_published"?: boolean; "number": number; "slug": string; "sort_order"?: number; "story_id": number; "title": string }
  "AdminChapterListResponse": { "results": Array<ApiSchemas["AdminChapter"]> }
  "AdminCompletions": { "adventure": number; "challenge": number; "total": number }
  "AdminContent": { "id": number; "kind": ApiSchemas["AdminContentKindEnum"]; "official_chapter": ApiSchemas["AdminOfficialChapterBrief"] | null; "slug": string; "status": string; "title": string; "updated_at": string; "visibility": string }
  "AdminContentKindEnum": "adventure" | "challenge" | "lesson"
  "AdminContentListResponse": { "results": Array<ApiSchemas["AdminContent"]> }
  "AdminEconomyAdjustRequest": { "amount": number; "reason": string; "request_id": string; "user_id": number }
  "AdminEconomyAdjustResponse": { "applied": boolean; "wallet": ApiSchemas["WalletSummary"] }
  "AdminFeatureFlag": { "description": string; "enabled": boolean; "key": ApiSchemas["KeyEnum"]; "label": string }
  "AdminFeatureFlagUpdateRequest": { "enabled": boolean; "key": ApiSchemas["KeyEnum"] }
  "AdminModerationContent": { "id": number; "kind": string; "owner": string | null; "title": string; "updated_at": string }
  "AdminModerationListResponse": { "content": Array<ApiSchemas["AdminModerationContent"]> }
  "AdminModerationUnpublishRequest": { "id": number; "kind": ApiSchemas["AdminModerationUnpublishRequestKindEnum"] }
  "AdminModerationUnpublishRequestKindEnum": "content"
  "AdminOfficialChapterBrief": { "id": number; "title": string }
  "AdminOkayResponse": { "ok": boolean }
  "AdminOverviewEconomy": { "coins_in_circulation": number; "coins_spent": number; "signup_grant": number }
  "AdminOverviewResponse": { "economy": ApiSchemas["AdminOverviewEconomy"]; "recent_admin_actions": Array<ApiSchemas["AdminRecentAction"]>; "recent_purchases": Array<ApiSchemas["AdminRecentPurchase"]>; "recent_signups": Array<ApiSchemas["AdminUserBrief"]>; "users": ApiSchemas["AdminOverviewUsers"] }
  "AdminOverviewUsers": { "new_30d": number; "new_7d": number; "total": number }
  "AdminRecentAction": { "action": string; "actor": string | null; "created_at": string; "id": number; "target_label": string }
  "AdminRecentPurchase": { "amount": number; "created_at": string; "reason": string; "user_id": number; "username": string }
  "AdminRunBreakdown": { "by_status": { [key: string]: number }; "passed": number; "total": number }
  "AdminRuns": { "adventure": ApiSchemas["AdminRunBreakdown"]; "by_status": { [key: string]: number }; "challenge": ApiSchemas["AdminRunBreakdown"]; "passed": number; "total": number }
  "AdminSettingsResponse": { "feature_flags": Array<ApiSchemas["AdminFeatureFlag"]> }
  "AdminStory": { "chapter_count": number; "difficulty": ApiSchemas["DifficultyEnum"]; "id": number; "is_published": boolean; "management_source": string; "prerequisite_story": ApiSchemas["AdminStoryPrerequisite"] | null; "price": number; "slug": string; "sort_order": number; "summary": string; "title": string; "world_slug": string }
  "AdminStoryAnalytics": { "adventure_runs": number; "challenge_runs": number; "passed": number; "runs": number; "slug": string; "title": string }
  "AdminStoryCreateRequest": { "difficulty"?: ApiSchemas["DifficultyEnum"]; "is_published"?: boolean; "prerequisite_story"?: number | null; "price"?: number; "slug": string; "sort_order"?: number; "summary"?: string; "title": string; "world_slug": string }
  "AdminStoryListResponse": { "results": Array<ApiSchemas["AdminStory"]>; "world_options": Array<string> }
  "AdminStoryPrerequisite": { "id": number; "slug": string; "title": string }
  "AdminTransaction": { "amount": number; "created_at": string; "id": number; "reason": string; "user_id": number; "username": string }
  "AdminTransactionListResponse": { "results": Array<ApiSchemas["AdminTransaction"]> }
  "AdminUserActionRequest": { "action": ApiSchemas["ActionEnum"]; "amount"?: number; "reason"?: string; "request_id"?: string; "value"?: boolean }
  "AdminUserBrief": { "date_joined": string; "email": string; "id": number; "is_active": boolean; "is_staff": boolean; "username": string }
  "AdminUserDetail": { "date_joined": string; "email": string; "entitlement_count": number; "id": number; "is_active": boolean; "is_staff": boolean; "last_login": string | null; "username": string; "wallet": ApiSchemas["WalletSummary"] }
  "AdminUserListResponse": { "results": Array<ApiSchemas["AdminUserBrief"]> }
  "AdventureCommandResponse": { "command_classification": string; "command_outcome": { [key: string]: JsonValue }; "exit_code": number; "run": ApiSchemas["AdventureCommandRunResponse"]; "solved": boolean; "stderr": string; "stdout": string; "step": ApiSchemas["RuntimeStepResponse"]; "terminal_output": string }
  "AdventureCommandRunResponse": ApiSchemas["AdventureRunResponse"] | ApiSchemas["AdventureRunPatchResponse"]
  "AdventureLevelLibraryResponse": { "book": { [key: string]: JsonValue }; "run": ApiSchemas["AdventureRunResponse"] }
  "AdventureLevelTierCommandResponse": { "command_family": string; "command_outcome": { [key: string]: JsonValue }; "diagnostic_metadata": Array<string>; "exit_code": number; "run": ApiSchemas["AdventureLevelTierCommandRunResponse"]; "stderr": string; "stdout": string; "step": ApiSchemas["AdventureLevelTierCommandStepResponse"] }
  "AdventureLevelTierCommandRunResponse": { "completed_at": string | null; "completion"?: { [key: string]: JsonValue } | null; "counts": { [key: string]: JsonValue }; "failure_reason": string | null; "id": number; "next_difficulty"?: { [key: string]: JsonValue } | null; "progress"?: { [key: string]: JsonValue }; "replay": boolean; "repository_state": { [key: string]: JsonValue }; "stars": number; "status": ApiSchemas["GameplayRunStatus"]; "visualization": { [key: string]: JsonValue } }
  "AdventureLevelTierCommandStepResponse": { "command_classification": string; "command_text": string; "contextual_feedback": string; "created_at": string; "evaluation_result": string; "id": number; "result_category": string; "terminal_output": string; "visualization_snapshot": { [key: string]: JsonValue } }
  "AdventureLevelTierRunResponse": { "chapter": { [key: string]: JsonValue } | null; "completed_at": string | null; "completion": { [key: string]: JsonValue } | null; "counts": { [key: string]: JsonValue }; "difficulty": string | null; "expected_state": { [key: string]: JsonValue } | null; "failure_reason": string | null; "id": number; "next_difficulty": { [key: string]: JsonValue } | null; "policy": { [key: string]: JsonValue }; "progress": { [key: string]: JsonValue }; "replay": boolean; "repository_state": { [key: string]: JsonValue }; "scaffolding": { [key: string]: JsonValue }; "scenario_context": { [key: string]: JsonValue }; "stars": number; "status": ApiSchemas["GameplayRunStatus"]; "steps": Array<ApiSchemas["AdventureLevelTierRunStepResponse"]>; "story": { [key: string]: JsonValue } | null; "tier": { [key: string]: JsonValue }; "variant": { [key: string]: JsonValue }; "visualization": { [key: string]: JsonValue } }
  "AdventureLevelTierRunStart": { "prior_run_id"?: number | null; "replay"?: boolean; "source_entry_point"?: ApiSchemas["SourceEntryPointEnum"] }
  "AdventureLevelTierRunStepResponse": { "command_classification": string; "command_text": string; "contextual_feedback": string; "created_at": string; "id": number; "result_category": string; "terminal_output": string; "visualization_snapshot": { [key: string]: JsonValue } }
  "AdventureRunPatchResponse": { "current_attempt": { [key: string]: JsonValue }; "id": number; "partial": ApiSchemas["PartialEnum"]; "status": ApiSchemas["GameplayRunStatus"] }
  "AdventureRunResponse": { "battle_stage": { [key: string]: JsonValue } | null; "chapter_id": number | null; "completed_at": string | null; "current_attempt": { [key: string]: JsonValue } | null; "current_level_index": number; "current_wave": number; "id": number; "is_passed": boolean; "library_opened": boolean; "mastery": { [key: string]: JsonValue }; "next_level": { [key: string]: JsonValue } | null; "passed": boolean; "progress": { [key: string]: JsonValue }; "replay": boolean; "results": Array<{ [key: string]: JsonValue }>; "selected_level": { [key: string]: JsonValue } | null; "stars": number; "status": ApiSchemas["GameplayRunStatus"]; "story": { [key: string]: JsonValue } | null; "total_levels": number; "total_waves": number }
  "ChallengeCommandResponse": { "command_family": string; "command_outcome": { [key: string]: JsonValue }; "diagnostic_metadata": Array<string>; "exit_code": number; "run": ApiSchemas["ChallengeCommandRunResponse"]; "stderr": string; "stdout": string; "step": ApiSchemas["ChallengeCommandStepResponse"] }
  "ChallengeCommandRunResponse": { "completed_at": string | null; "completion"?: { [key: string]: JsonValue } | null; "counts": { [key: string]: JsonValue }; "failure_reason": string | null; "id": number; "mastery_progress"?: { [key: string]: JsonValue }; "next_difficulty"?: { [key: string]: JsonValue } | null; "replay": boolean; "repository_state": { [key: string]: JsonValue }; "sibling_levels"?: Array<{ [key: string]: JsonValue }>; "stars": number; "status": ApiSchemas["GameplayRunStatus"]; "visualization": { [key: string]: JsonValue } }
  "ChallengeCommandStepResponse": { "command_classification": string; "command_text": string; "contextual_feedback": string; "created_at": string; "evaluation_result": string; "id": number; "result_category": string; "terminal_output": string; "visualization_snapshot": { [key: string]: JsonValue } }
  "ChallengeRunResponse": { "challenge": { [key: string]: JsonValue }; "chapter": { [key: string]: JsonValue }; "completed_at": string | null; "completion": { [key: string]: JsonValue } | null; "counts": { [key: string]: JsonValue }; "difficulty": string | null; "expected_state": { [key: string]: JsonValue } | null; "failure_reason": string | null; "id": number; "mastery_progress": { [key: string]: JsonValue }; "next_difficulty": { [key: string]: JsonValue } | null; "policy": { [key: string]: JsonValue }; "replay": boolean; "repository_state": { [key: string]: JsonValue }; "reward_coins": number; "scaffolding": { [key: string]: JsonValue }; "scenario_context": { [key: string]: JsonValue }; "sibling_levels": Array<{ [key: string]: JsonValue }>; "stars": number; "status": ApiSchemas["GameplayRunStatus"]; "steps": Array<ApiSchemas["ChallengeRunStepResponse"]>; "story": { [key: string]: JsonValue } | null; "variant": { [key: string]: JsonValue }; "visualization": { [key: string]: JsonValue } }
  "ChallengeRunStart": { "prior_run_id"?: number | null; "replay"?: boolean; "source_entry_point"?: ApiSchemas["SourceEntryPointEnum"] }
  "ChallengeRunStepResponse": { "command_classification": string; "command_text": string; "contextual_feedback": string; "created_at": string; "id": number; "result_category": string; "terminal_output": string; "visualization_snapshot": { [key: string]: JsonValue } }
  "ChapterChestReward": { "coins": number; "threshold": number }
  "ChapterLevelCompletion": { "denominator": number; "numerator": number; "value": number }
  "ChapterList": { "adventure_level_count": number; "challenge_count": number; "chest_schedule": Array<ApiSchemas["ChapterChestReward"]>; "command_skill_count": number; "description": string; "id": number; "is_orientation": boolean; "is_playable": boolean; "level_completion": ApiSchemas["ChapterLevelCompletion"]; "lock_reason": string; "locked": boolean; "number": number; "slug": string; "sort_order": number; "story": ApiSchemas["ChapterStory"] | null; "title": string }
  "ChapterOrientationComplete": { "highest_step_seen": number }
  "ChapterOrientationLessonDetail": { "content_html": string; "highest_step_seen": number; "id": number; "interaction_steps": JsonValue; "is_complete": boolean; "scoped_css": string; "slug": string; "sort_order": number; "subtitle": string; "title": string }
  "ChapterOrientationLessonList": { "id": number; "is_complete": boolean; "slug": string; "sort_order": number; "subtitle": string; "title": string }
  "ChapterStory": { "id": number; "slug": string; "title": string; "world_slug": string }
  "ClientCommandExecution": { "client_run_revision"?: number | null; "command_family": string; "diagnostic": boolean; "diagnostic_metadata": Array<string>; "exit_code": number; "next_state": { [key: string]: JsonValue }; "normalized_command": string; "output": string; "processed": boolean; "stderr": string; "stdout": string }
  "CommandFormPreviewResponse": { "command_preview": { [key: string]: JsonValue }; "id": number; "is_playable": boolean; "label": string; "skill": ApiSchemas["CommandFormPreviewSkillResponse"]; "slug": string; "summary": string; "usage_form": string }
  "CommandFormPreviewSkillResponse": { "base_command": string; "id": number; "slug": string; "title": string }
  "CommandSubmit": { "command": string; "execution": ApiSchemas["ClientCommandExecution"] }
  "ContentDefinition": { "chapter_id": number | null; "command_family": string; "created_at": string; "definition": { [key: string]: JsonValue }; "difficulty": string; "id": number; "kind": ApiSchemas["KindA5eEnum"]; "official_chapter_id": number | null; "owner_id": number | null; "published_at": string | null; "slug": string; "source_definition_id": number | null; "status": ApiSchemas["StatusEnum"]; "summary": string; "tags": Array<string>; "title": string; "updated_at": string; "validation_errors": Array<ApiSchemas["ValidationErrorRow"]>; "visibility": ApiSchemas["VisibilityEnum"] }
  "ContentDefinitionCreateRequest": { "chapter"?: number | null; "command_family"?: string; "definition"?: { [key: string]: JsonValue }; "difficulty"?: string; "kind": ApiSchemas["KindA5eEnum"]; "official_chapter"?: number | null; "slug": string; "summary"?: string; "tags"?: Array<string>; "title": string; "visibility"?: ApiSchemas["VisibilityEnum"] }
  "ContentDefinitionListResponse": { "results": Array<ApiSchemas["ContentDefinitionSummary"]> }
  "ContentDefinitionSummary": { "chapter_id": number | null; "command_family": string; "created_at": string; "difficulty": string; "id": number; "kind": ApiSchemas["KindA5eEnum"]; "official_chapter_id": number | null; "owner_id": number | null; "published_at": string | null; "slug": string; "source_definition_id": number | null; "status": ApiSchemas["StatusEnum"]; "summary": string; "tags": Array<string>; "title": string; "updated_at": string; "validation_errors": Array<ApiSchemas["ValidationErrorRow"]>; "visibility": ApiSchemas["VisibilityEnum"] }
  "ContentTestRunResult": { "kind": ApiSchemas["KindA5eEnum"]; "pages"?: Array<JsonValue>; "runtime_id": number | null; "start_path"?: string | null }
  "ContentValidationResult": { "errors": Array<ApiSchemas["ValidationErrorRow"]>; "valid": boolean }
  "DashboardCounts": { "abandoned": number; "completed": number; "failed": number; "started": number }
  "DashboardKpiSet": { "arc": ApiSchemas["RateMetric"]; "hlcr": ApiSchemas["RateMetric"]; "scr": ApiSchemas["RateMetric"] }
  "DashboardRetryTrend": { "attempts": number; "label": string; "level_title": string; "retries": number }
  "DashboardStreak": { "current": number; "last_completed_on": string | null; "longest": number }
  "DashboardSummaryResponse": { "chapter_kpis": { [key: string]: ApiSchemas["DashboardKpiSet"] }; "completed_stories": Array<string>; "completed_story_slug": string | null; "counts": ApiSchemas["DashboardCounts"]; "kpis": ApiSchemas["DashboardKpiSet"]; "mastery": number; "perfect_clears": number; "retry_trends": Array<ApiSchemas["DashboardRetryTrend"]>; "streak": ApiSchemas["DashboardStreak"] }
  "DetailResponse": { "detail": string }
  "DifficultyEnum": "beginner" | "intermediate" | "advanced"
  "GameplayRunStatus": "started" | "completed" | "failed" | "abandoned"
  "KeyEnum": "shop-purchases"
  "KindA5eEnum": "adventure" | "challenge" | "lesson"
  "LearnedSkillResponse": { "base_command": string; "chapter_id"?: number | null; "chapter_number": number; "chapter_title": string; "id": number; "slug": string; "summary": string; "title": string }
  "LearnedSkillsResponse": { "results": Array<ApiSchemas["LearnedSkillResponse"]> }
  "Login": { "identifier": string; "password": string }
  "MotionModeEnum": "system" | "reduced" | "full"
  "OnboardingPhaseEnum": "stories" | "shop" | "purchase" | "home" | "equip" | "done"
  "PartialEnum": true
  "PasswordChange": { "current_password": string; "password": string; "password_confirm": string }
  "PasswordResetConfirm": { "password": string; "password_confirm": string; "token": string; "uid": string }
  "PasswordResetRequest": { "email": string }
  "PatchedAdminChapterUpdateRequest": { "battle_stage"?: { [key: string]: JsonValue }; "description"?: string; "is_playable"?: boolean; "is_published"?: boolean; "number"?: number; "sort_order"?: number; "title"?: string }
  "PatchedAdminStoryUpdateRequest": { "difficulty"?: ApiSchemas["DifficultyEnum"]; "is_published"?: boolean; "prerequisite_story"?: number | null; "price"?: number; "sort_order"?: number; "summary"?: string; "title"?: string; "world_slug"?: string }
  "PatchedContentDefinitionUpdateRequest": { "chapter"?: number | null; "command_family"?: string; "definition"?: { [key: string]: JsonValue }; "difficulty"?: string; "kind"?: ApiSchemas["KindA5eEnum"]; "official_chapter"?: number | null; "slug"?: string; "summary"?: string; "tags"?: Array<string>; "title"?: string; "visibility"?: ApiSchemas["VisibilityEnum"] }
  "PatchedPlayerPreferences": { "motion_mode"?: ApiSchemas["MotionModeEnum"]; "onboarding_phase"?: ApiSchemas["OnboardingPhaseEnum"] }
  "PlayerPreferences": { "motion_mode"?: ApiSchemas["MotionModeEnum"]; "onboarding_phase"?: ApiSchemas["OnboardingPhaseEnum"] }
  "RateMetric": { "denominator": number; "numerator": number; "value": number | null }
  "Register": { "email": string; "password": string; "password_confirm": string; "username": string }
  "RegisterResponse": { "user": ApiSchemas["User"] }
  "RuntimeStepResponse": { "command_text": string; "id": number; "result_category": string; "terminal_output": string }
  "SessionResponse": { "access": string; "user": ApiSchemas["User"] }
  "ShopEquipResponse": { "active_companion": string | null; "shop": ApiSchemas["ShopResponse"] }
  "ShopItemResponse": { "active": boolean; "kind": ApiSchemas["ShopItemResponseKindEnum"]; "label": string; "owned": boolean; "price": number; "slug": string; "unlocks_story"?: ApiSchemas["ShopUnlockResponse"] }
  "ShopItemResponseKindEnum": "story" | "companion"
  "ShopMutationRequest": { "kind": string; "slug": string }
  "ShopPurchaseResponse": { "owned": boolean; "shop": ApiSchemas["ShopResponse"]; "wallet": ApiSchemas["WalletSummaryResponse"] }
  "ShopResponse": { "active_companion": string | null; "items": Array<ApiSchemas["ShopItemResponse"]>; "purchases_enabled": boolean }
  "ShopUnlockResponse": { "chapter_count": number; "difficulty": ApiSchemas["DifficultyEnum"]; "prerequisite_story": string | null; "slug": string; "title": string; "world_slug": string }
  "SourceEntryPointEnum": "level_page" | "retry"
  "StatsHeadline": { "accuracy": number | null; "boss_floors": ApiSchemas["StatsScopedCount"]; "comebacks": ApiSchemas["StatsScopedCount"]; "commands_run": number; "day_streak": number; "finish_rate": ApiSchemas["RateMetric"]; "gitcoins": number; "levels_completed": number; "longest_streak": number; "perfect_clears": number }
  "StatsScopedCount": { "scope": string; "value": number }
  "StatsSkillAxis": { "command": string; "hint": string; "key": string; "label": string; "value": number | null }
  "StatsSummaryResponse": { "activity_trend": Array<ApiSchemas["StatsTrendPoint"]>; "headline": ApiSchemas["StatsHeadline"]; "skill_profile": Array<ApiSchemas["StatsSkillAxis"]> }
  "StatsTrendPoint": { "commands_run": number; "date": string; "levels_completed": number }
  "StatusEnum": "draft" | "testable" | "published" | "archived"
  "Story": { "completed": boolean; "difficulty": ApiSchemas["DifficultyEnum"]; "id": number; "is_published": boolean; "lock_reason": string; "locked": boolean; "owned": boolean; "prerequisite_story": ApiSchemas["StoryPrerequisite"] | null; "price": number; "slug": string; "sort_order": number; "summary": string; "title": string; "world_slug": string }
  "StoryPrerequisite": { "completed": boolean; "slug": string; "title": string }
  "User": { "email": string; "id": number; "is_staff": boolean; "username": string }
  "ValidationErrorRow": { "field": string; "message": string }
  "VisibilityEnum": "private" | "public"
  "WalletSummary": { "balance": number }
  "WalletSummaryResponse": { "balance": number }
  "WorkspaceFile": { "content"?: string; "path": string }
  "WorkspaceFileRename": { "new_path": string; "path": string }
}

export type ApiPath =
  | "/api/admin/analytics/"
  | "/api/admin/chapters/"
  | "/api/admin/chapters/{chapter_id}/"
  | "/api/admin/content/"
  | "/api/admin/economy/adjust/"
  | "/api/admin/economy/transactions/"
  | "/api/admin/moderation/"
  | "/api/admin/moderation/unpublish/"
  | "/api/admin/overview/"
  | "/api/admin/settings/"
  | "/api/admin/stories/"
  | "/api/admin/stories/{story_id}/"
  | "/api/admin/users/"
  | "/api/admin/users/{user_id}/"
  | "/api/admin/users/{user_id}/actions/"
  | "/api/adventure-level-tiers/{tier_id}/runs/"
  | "/api/adventure-levels/{level_id}/runs/"
  | "/api/adventure-runs/{run_id}/"
  | "/api/adventure-runs/{run_id}/files/"
  | "/api/adventure-runs/{run_id}/level-library/"
  | "/api/adventure-runs/{run_id}/submit-command/"
  | "/api/adventure-tier-runs/{run_id}/"
  | "/api/adventure-tier-runs/{run_id}/files/"
  | "/api/adventure-tier-runs/{run_id}/retry/"
  | "/api/adventure-tier-runs/{run_id}/submit-command/"
  | "/api/adventures/{adventure_slug}/runs/"
  | "/api/auth/login/"
  | "/api/auth/logout/"
  | "/api/auth/me/"
  | "/api/auth/password-change/"
  | "/api/auth/password-reset/confirm/"
  | "/api/auth/password-reset/request/"
  | "/api/auth/refresh/"
  | "/api/auth/register/"
  | "/api/auth/sessions/revoke-all/"
  | "/api/auth/sessions/revoke-others/"
  | "/api/authoring/chapters/"
  | "/api/authoring/chapters/{chapter_id}/"
  | "/api/authoring/command-forms/"
  | "/api/authoring/content-definitions/"
  | "/api/authoring/content-definitions/{definition_id}/"
  | "/api/authoring/content-definitions/{definition_id}/publish/"
  | "/api/authoring/content-definitions/{definition_id}/remix/"
  | "/api/authoring/content-definitions/{definition_id}/test-run/"
  | "/api/authoring/content-definitions/{definition_id}/validate/"
  | "/api/challenge-runs/{run_id}/"
  | "/api/challenge-runs/{run_id}/files/"
  | "/api/challenge-runs/{run_id}/retry/"
  | "/api/challenge-runs/{run_id}/submit-command/"
  | "/api/challenge-trials/{trial_id}/runs/"
  | "/api/chapters/"
  | "/api/chapters/{chapter_id}/book/"
  | "/api/chapters/{chapter_id}/orientation/"
  | "/api/chapters/{chapter_id}/overview/"
  | "/api/command-forms/{form_id}/preview/"
  | "/api/health/"
  | "/api/health/live/"
  | "/api/health/ready/"
  | "/api/orientation-lessons/{lesson_id}/"
  | "/api/orientation-lessons/{lesson_id}/complete/"
  | "/api/player/loadout/companion/"
  | "/api/player/preferences/"
  | "/api/progress/dashboard/"
  | "/api/progress/stats/"
  | "/api/progress/wallet/"
  | "/api/schema/"
  | "/api/shop/catalog/"
  | "/api/shop/catalog/purchase/"
  | "/api/skills/learned/"
  | "/api/stories/"

export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS'

export type ApiMethodByPath = {
  "/api/admin/analytics/": "GET"
  "/api/admin/chapters/": "GET" | "POST"
  "/api/admin/chapters/{chapter_id}/": "PATCH"
  "/api/admin/content/": "GET"
  "/api/admin/economy/adjust/": "POST"
  "/api/admin/economy/transactions/": "GET"
  "/api/admin/moderation/": "GET"
  "/api/admin/moderation/unpublish/": "POST"
  "/api/admin/overview/": "GET"
  "/api/admin/settings/": "GET" | "POST"
  "/api/admin/stories/": "GET" | "POST"
  "/api/admin/stories/{story_id}/": "PATCH"
  "/api/admin/users/": "GET"
  "/api/admin/users/{user_id}/": "GET"
  "/api/admin/users/{user_id}/actions/": "POST"
  "/api/adventure-level-tiers/{tier_id}/runs/": "POST"
  "/api/adventure-levels/{level_id}/runs/": "POST"
  "/api/adventure-runs/{run_id}/": "DELETE" | "GET"
  "/api/adventure-runs/{run_id}/files/": "DELETE" | "PATCH" | "POST" | "PUT"
  "/api/adventure-runs/{run_id}/level-library/": "POST"
  "/api/adventure-runs/{run_id}/submit-command/": "POST"
  "/api/adventure-tier-runs/{run_id}/": "DELETE" | "GET"
  "/api/adventure-tier-runs/{run_id}/files/": "DELETE" | "PATCH" | "POST" | "PUT"
  "/api/adventure-tier-runs/{run_id}/retry/": "POST"
  "/api/adventure-tier-runs/{run_id}/submit-command/": "POST"
  "/api/adventures/{adventure_slug}/runs/": "POST"
  "/api/auth/login/": "POST"
  "/api/auth/logout/": "POST"
  "/api/auth/me/": "GET"
  "/api/auth/password-change/": "POST"
  "/api/auth/password-reset/confirm/": "POST"
  "/api/auth/password-reset/request/": "POST"
  "/api/auth/refresh/": "POST"
  "/api/auth/register/": "POST"
  "/api/auth/sessions/revoke-all/": "POST"
  "/api/auth/sessions/revoke-others/": "POST"
  "/api/authoring/chapters/": "GET" | "POST"
  "/api/authoring/chapters/{chapter_id}/": "DELETE" | "PATCH"
  "/api/authoring/command-forms/": "GET"
  "/api/authoring/content-definitions/": "GET" | "POST"
  "/api/authoring/content-definitions/{definition_id}/": "GET" | "PATCH"
  "/api/authoring/content-definitions/{definition_id}/publish/": "POST"
  "/api/authoring/content-definitions/{definition_id}/remix/": "POST"
  "/api/authoring/content-definitions/{definition_id}/test-run/": "POST"
  "/api/authoring/content-definitions/{definition_id}/validate/": "POST"
  "/api/challenge-runs/{run_id}/": "DELETE" | "GET"
  "/api/challenge-runs/{run_id}/files/": "DELETE" | "PATCH" | "POST" | "PUT"
  "/api/challenge-runs/{run_id}/retry/": "POST"
  "/api/challenge-runs/{run_id}/submit-command/": "POST"
  "/api/challenge-trials/{trial_id}/runs/": "POST"
  "/api/chapters/": "GET"
  "/api/chapters/{chapter_id}/book/": "GET"
  "/api/chapters/{chapter_id}/orientation/": "GET"
  "/api/chapters/{chapter_id}/overview/": "GET"
  "/api/command-forms/{form_id}/preview/": "GET"
  "/api/health/": "GET"
  "/api/health/live/": "GET"
  "/api/health/ready/": "GET"
  "/api/orientation-lessons/{lesson_id}/": "GET"
  "/api/orientation-lessons/{lesson_id}/complete/": "POST"
  "/api/player/loadout/companion/": "POST"
  "/api/player/preferences/": "GET" | "PATCH"
  "/api/progress/dashboard/": "GET"
  "/api/progress/stats/": "GET"
  "/api/progress/wallet/": "GET"
  "/api/schema/": "GET"
  "/api/shop/catalog/": "GET"
  "/api/shop/catalog/purchase/": "POST"
  "/api/skills/learned/": "GET"
  "/api/stories/": "GET"
}

export const apiOperations = {
  admin_analytics_retrieve: { method: "GET", path: "/api/admin/analytics/", operationId: "admin_analytics_retrieve", tags: ["admin"] },
  admin_chapters_retrieve: { method: "GET", path: "/api/admin/chapters/", operationId: "admin_chapters_retrieve", tags: ["admin"] },
  admin_chapters_create: { method: "POST", path: "/api/admin/chapters/", operationId: "admin_chapters_create", tags: ["admin"] },
  admin_chapters_partial_update: { method: "PATCH", path: "/api/admin/chapters/{chapter_id}/", operationId: "admin_chapters_partial_update", tags: ["admin"] },
  admin_content_retrieve: { method: "GET", path: "/api/admin/content/", operationId: "admin_content_retrieve", tags: ["admin"] },
  admin_economy_adjust_create: { method: "POST", path: "/api/admin/economy/adjust/", operationId: "admin_economy_adjust_create", tags: ["admin"] },
  admin_economy_transactions_retrieve: { method: "GET", path: "/api/admin/economy/transactions/", operationId: "admin_economy_transactions_retrieve", tags: ["admin"] },
  admin_moderation_retrieve: { method: "GET", path: "/api/admin/moderation/", operationId: "admin_moderation_retrieve", tags: ["admin"] },
  admin_moderation_unpublish_create: { method: "POST", path: "/api/admin/moderation/unpublish/", operationId: "admin_moderation_unpublish_create", tags: ["admin"] },
  admin_overview_retrieve: { method: "GET", path: "/api/admin/overview/", operationId: "admin_overview_retrieve", tags: ["admin"] },
  admin_settings_retrieve: { method: "GET", path: "/api/admin/settings/", operationId: "admin_settings_retrieve", tags: ["admin"] },
  admin_settings_create: { method: "POST", path: "/api/admin/settings/", operationId: "admin_settings_create", tags: ["admin"] },
  admin_stories_retrieve: { method: "GET", path: "/api/admin/stories/", operationId: "admin_stories_retrieve", tags: ["admin"] },
  admin_stories_create: { method: "POST", path: "/api/admin/stories/", operationId: "admin_stories_create", tags: ["admin"] },
  admin_stories_partial_update: { method: "PATCH", path: "/api/admin/stories/{story_id}/", operationId: "admin_stories_partial_update", tags: ["admin"] },
  admin_users_retrieve: { method: "GET", path: "/api/admin/users/", operationId: "admin_users_retrieve", tags: ["admin"] },
  admin_users_retrieve_2: { method: "GET", path: "/api/admin/users/{user_id}/", operationId: "admin_users_retrieve_2", tags: ["admin"] },
  admin_users_actions_create: { method: "POST", path: "/api/admin/users/{user_id}/actions/", operationId: "admin_users_actions_create", tags: ["admin"] },
  adventure_level_tiers_runs_create: { method: "POST", path: "/api/adventure-level-tiers/{tier_id}/runs/", operationId: "adventure_level_tiers_runs_create", tags: ["adventure-level-tiers"] },
  adventure_levels_runs_create: { method: "POST", path: "/api/adventure-levels/{level_id}/runs/", operationId: "adventure_levels_runs_create", tags: ["adventure-levels"] },
  adventure_runs_destroy: { method: "DELETE", path: "/api/adventure-runs/{run_id}/", operationId: "adventure_runs_destroy", tags: ["adventure-runs"] },
  adventure_runs_retrieve: { method: "GET", path: "/api/adventure-runs/{run_id}/", operationId: "adventure_runs_retrieve", tags: ["adventure-runs"] },
  adventure_runs_files_destroy: { method: "DELETE", path: "/api/adventure-runs/{run_id}/files/", operationId: "adventure_runs_files_destroy", tags: ["adventure-runs"] },
  adventure_runs_files_partial_update: { method: "PATCH", path: "/api/adventure-runs/{run_id}/files/", operationId: "adventure_runs_files_partial_update", tags: ["adventure-runs"] },
  adventure_runs_files_create: { method: "POST", path: "/api/adventure-runs/{run_id}/files/", operationId: "adventure_runs_files_create", tags: ["adventure-runs"] },
  adventure_runs_files_update: { method: "PUT", path: "/api/adventure-runs/{run_id}/files/", operationId: "adventure_runs_files_update", tags: ["adventure-runs"] },
  adventure_runs_level_library_create: { method: "POST", path: "/api/adventure-runs/{run_id}/level-library/", operationId: "adventure_runs_level_library_create", tags: ["adventure-runs"] },
  adventure_runs_submit_command_create: { method: "POST", path: "/api/adventure-runs/{run_id}/submit-command/", operationId: "adventure_runs_submit_command_create", tags: ["adventure-runs"] },
  adventure_tier_runs_destroy: { method: "DELETE", path: "/api/adventure-tier-runs/{run_id}/", operationId: "adventure_tier_runs_destroy", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_retrieve: { method: "GET", path: "/api/adventure-tier-runs/{run_id}/", operationId: "adventure_tier_runs_retrieve", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_files_destroy: { method: "DELETE", path: "/api/adventure-tier-runs/{run_id}/files/", operationId: "adventure_tier_runs_files_destroy", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_files_partial_update: { method: "PATCH", path: "/api/adventure-tier-runs/{run_id}/files/", operationId: "adventure_tier_runs_files_partial_update", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_files_create: { method: "POST", path: "/api/adventure-tier-runs/{run_id}/files/", operationId: "adventure_tier_runs_files_create", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_files_update: { method: "PUT", path: "/api/adventure-tier-runs/{run_id}/files/", operationId: "adventure_tier_runs_files_update", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_retry_create: { method: "POST", path: "/api/adventure-tier-runs/{run_id}/retry/", operationId: "adventure_tier_runs_retry_create", tags: ["adventure-tier-runs"] },
  adventure_tier_runs_submit_command_create: { method: "POST", path: "/api/adventure-tier-runs/{run_id}/submit-command/", operationId: "adventure_tier_runs_submit_command_create", tags: ["adventure-tier-runs"] },
  adventures_runs_create: { method: "POST", path: "/api/adventures/{adventure_slug}/runs/", operationId: "adventures_runs_create", tags: ["adventures"] },
  auth_login_create: { method: "POST", path: "/api/auth/login/", operationId: "auth_login_create", tags: ["auth"] },
  auth_logout_create: { method: "POST", path: "/api/auth/logout/", operationId: "auth_logout_create", tags: ["auth"] },
  auth_me_retrieve: { method: "GET", path: "/api/auth/me/", operationId: "auth_me_retrieve", tags: ["auth"] },
  auth_password_change_create: { method: "POST", path: "/api/auth/password-change/", operationId: "auth_password_change_create", tags: ["auth"] },
  auth_password_reset_confirm_create: { method: "POST", path: "/api/auth/password-reset/confirm/", operationId: "auth_password_reset_confirm_create", tags: ["auth"] },
  auth_password_reset_request_create: { method: "POST", path: "/api/auth/password-reset/request/", operationId: "auth_password_reset_request_create", tags: ["auth"] },
  auth_refresh_create: { method: "POST", path: "/api/auth/refresh/", operationId: "auth_refresh_create", tags: ["auth"] },
  auth_register_create: { method: "POST", path: "/api/auth/register/", operationId: "auth_register_create", tags: ["auth"] },
  auth_sessions_revoke_all_create: { method: "POST", path: "/api/auth/sessions/revoke-all/", operationId: "auth_sessions_revoke_all_create", tags: ["auth"] },
  auth_sessions_revoke_others_create: { method: "POST", path: "/api/auth/sessions/revoke-others/", operationId: "auth_sessions_revoke_others_create", tags: ["auth"] },
  authoring_chapters_retrieve: { method: "GET", path: "/api/authoring/chapters/", operationId: "authoring_chapters_retrieve", tags: ["authoring"] },
  authoring_chapters_create: { method: "POST", path: "/api/authoring/chapters/", operationId: "authoring_chapters_create", tags: ["authoring"] },
  authoring_chapters_destroy: { method: "DELETE", path: "/api/authoring/chapters/{chapter_id}/", operationId: "authoring_chapters_destroy", tags: ["authoring"] },
  authoring_chapters_partial_update: { method: "PATCH", path: "/api/authoring/chapters/{chapter_id}/", operationId: "authoring_chapters_partial_update", tags: ["authoring"] },
  authoring_command_forms_retrieve: { method: "GET", path: "/api/authoring/command-forms/", operationId: "authoring_command_forms_retrieve", tags: ["authoring"] },
  authoring_content_definitions_retrieve: { method: "GET", path: "/api/authoring/content-definitions/", operationId: "authoring_content_definitions_retrieve", tags: ["authoring"] },
  authoring_content_definitions_create: { method: "POST", path: "/api/authoring/content-definitions/", operationId: "authoring_content_definitions_create", tags: ["authoring"] },
  authoring_content_definitions_retrieve_2: { method: "GET", path: "/api/authoring/content-definitions/{definition_id}/", operationId: "authoring_content_definitions_retrieve_2", tags: ["authoring"] },
  authoring_content_definitions_partial_update: { method: "PATCH", path: "/api/authoring/content-definitions/{definition_id}/", operationId: "authoring_content_definitions_partial_update", tags: ["authoring"] },
  authoring_content_definitions_publish_create: { method: "POST", path: "/api/authoring/content-definitions/{definition_id}/publish/", operationId: "authoring_content_definitions_publish_create", tags: ["authoring"] },
  authoring_content_definitions_remix_create: { method: "POST", path: "/api/authoring/content-definitions/{definition_id}/remix/", operationId: "authoring_content_definitions_remix_create", tags: ["authoring"] },
  authoring_content_definitions_test_run_create: { method: "POST", path: "/api/authoring/content-definitions/{definition_id}/test-run/", operationId: "authoring_content_definitions_test_run_create", tags: ["authoring"] },
  authoring_content_definitions_validate_create: { method: "POST", path: "/api/authoring/content-definitions/{definition_id}/validate/", operationId: "authoring_content_definitions_validate_create", tags: ["authoring"] },
  challenge_runs_destroy: { method: "DELETE", path: "/api/challenge-runs/{run_id}/", operationId: "challenge_runs_destroy", tags: ["challenge-runs"] },
  challenge_runs_retrieve: { method: "GET", path: "/api/challenge-runs/{run_id}/", operationId: "challenge_runs_retrieve", tags: ["challenge-runs"] },
  challenge_runs_files_destroy: { method: "DELETE", path: "/api/challenge-runs/{run_id}/files/", operationId: "challenge_runs_files_destroy", tags: ["challenge-runs"] },
  challenge_runs_files_partial_update: { method: "PATCH", path: "/api/challenge-runs/{run_id}/files/", operationId: "challenge_runs_files_partial_update", tags: ["challenge-runs"] },
  challenge_runs_files_create: { method: "POST", path: "/api/challenge-runs/{run_id}/files/", operationId: "challenge_runs_files_create", tags: ["challenge-runs"] },
  challenge_runs_files_update: { method: "PUT", path: "/api/challenge-runs/{run_id}/files/", operationId: "challenge_runs_files_update", tags: ["challenge-runs"] },
  challenge_runs_retry_create: { method: "POST", path: "/api/challenge-runs/{run_id}/retry/", operationId: "challenge_runs_retry_create", tags: ["challenge-runs"] },
  challenge_runs_submit_command_create: { method: "POST", path: "/api/challenge-runs/{run_id}/submit-command/", operationId: "challenge_runs_submit_command_create", tags: ["challenge-runs"] },
  challenge_trials_runs_create: { method: "POST", path: "/api/challenge-trials/{trial_id}/runs/", operationId: "challenge_trials_runs_create", tags: ["challenge-trials"] },
  chapters_list: { method: "GET", path: "/api/chapters/", operationId: "chapters_list", tags: ["chapters"] },
  chapters_book_retrieve: { method: "GET", path: "/api/chapters/{chapter_id}/book/", operationId: "chapters_book_retrieve", tags: ["chapters"] },
  chapters_orientation_list: { method: "GET", path: "/api/chapters/{chapter_id}/orientation/", operationId: "chapters_orientation_list", tags: ["chapters"] },
  chapters_overview_retrieve: { method: "GET", path: "/api/chapters/{chapter_id}/overview/", operationId: "chapters_overview_retrieve", tags: ["chapters"] },
  command_forms_preview_retrieve: { method: "GET", path: "/api/command-forms/{form_id}/preview/", operationId: "command_forms_preview_retrieve", tags: ["command-forms"] },
  health_retrieve: { method: "GET", path: "/api/health/", operationId: "health_retrieve", tags: ["health"] },
  health_live_retrieve: { method: "GET", path: "/api/health/live/", operationId: "health_live_retrieve", tags: ["health"] },
  health_ready_retrieve: { method: "GET", path: "/api/health/ready/", operationId: "health_ready_retrieve", tags: ["health"] },
  orientation_lessons_retrieve: { method: "GET", path: "/api/orientation-lessons/{lesson_id}/", operationId: "orientation_lessons_retrieve", tags: ["orientation-lessons"] },
  orientation_lessons_complete_create: { method: "POST", path: "/api/orientation-lessons/{lesson_id}/complete/", operationId: "orientation_lessons_complete_create", tags: ["orientation-lessons"] },
  player_loadout_companion_create: { method: "POST", path: "/api/player/loadout/companion/", operationId: "player_loadout_companion_create", tags: ["player"] },
  player_preferences_retrieve: { method: "GET", path: "/api/player/preferences/", operationId: "player_preferences_retrieve", tags: ["player"] },
  player_preferences_partial_update: { method: "PATCH", path: "/api/player/preferences/", operationId: "player_preferences_partial_update", tags: ["player"] },
  progress_dashboard_retrieve: { method: "GET", path: "/api/progress/dashboard/", operationId: "progress_dashboard_retrieve", tags: ["progress"] },
  progress_stats_retrieve: { method: "GET", path: "/api/progress/stats/", operationId: "progress_stats_retrieve", tags: ["progress"] },
  progress_wallet_retrieve: { method: "GET", path: "/api/progress/wallet/", operationId: "progress_wallet_retrieve", tags: ["progress"] },
  schema_retrieve: { method: "GET", path: "/api/schema/", operationId: "schema_retrieve", tags: ["schema"] },
  shop_catalog_retrieve: { method: "GET", path: "/api/shop/catalog/", operationId: "shop_catalog_retrieve", tags: ["shop"] },
  shop_catalog_purchase_create: { method: "POST", path: "/api/shop/catalog/purchase/", operationId: "shop_catalog_purchase_create", tags: ["shop"] },
  skills_learned_retrieve: { method: "GET", path: "/api/skills/learned/", operationId: "skills_learned_retrieve", tags: ["skills"] },
  stories_list: { method: "GET", path: "/api/stories/", operationId: "stories_list", tags: ["stories"] },
} as const

export type ApiOperationId = keyof typeof apiOperations
export type ApiOperation = (typeof apiOperations)[ApiOperationId]

export type ApiRequestBodyByOperation = {
  admin_analytics_retrieve: null
  admin_chapters_retrieve: null
  admin_chapters_create: ApiSchemas["AdminChapterCreateRequest"]
  admin_chapters_partial_update: ApiSchemas["PatchedAdminChapterUpdateRequest"]
  admin_content_retrieve: null
  admin_economy_adjust_create: ApiSchemas["AdminEconomyAdjustRequest"]
  admin_economy_transactions_retrieve: null
  admin_moderation_retrieve: null
  admin_moderation_unpublish_create: ApiSchemas["AdminModerationUnpublishRequest"]
  admin_overview_retrieve: null
  admin_settings_retrieve: null
  admin_settings_create: ApiSchemas["AdminFeatureFlagUpdateRequest"]
  admin_stories_retrieve: null
  admin_stories_create: ApiSchemas["AdminStoryCreateRequest"]
  admin_stories_partial_update: ApiSchemas["PatchedAdminStoryUpdateRequest"]
  admin_users_retrieve: null
  admin_users_retrieve_2: null
  admin_users_actions_create: ApiSchemas["AdminUserActionRequest"]
  adventure_level_tiers_runs_create: ApiSchemas["AdventureLevelTierRunStart"]
  adventure_levels_runs_create: null
  adventure_runs_destroy: null
  adventure_runs_retrieve: null
  adventure_runs_files_destroy: null
  adventure_runs_files_partial_update: ApiSchemas["WorkspaceFile"]
  adventure_runs_files_create: ApiSchemas["WorkspaceFile"]
  adventure_runs_files_update: ApiSchemas["WorkspaceFileRename"]
  adventure_runs_level_library_create: null
  adventure_runs_submit_command_create: ApiSchemas["CommandSubmit"]
  adventure_tier_runs_destroy: null
  adventure_tier_runs_retrieve: null
  adventure_tier_runs_files_destroy: null
  adventure_tier_runs_files_partial_update: ApiSchemas["WorkspaceFile"]
  adventure_tier_runs_files_create: ApiSchemas["WorkspaceFile"]
  adventure_tier_runs_files_update: ApiSchemas["WorkspaceFileRename"]
  adventure_tier_runs_retry_create: null
  adventure_tier_runs_submit_command_create: ApiSchemas["CommandSubmit"]
  adventures_runs_create: null
  auth_login_create: ApiSchemas["Login"]
  auth_logout_create: null
  auth_me_retrieve: null
  auth_password_change_create: ApiSchemas["PasswordChange"]
  auth_password_reset_confirm_create: ApiSchemas["PasswordResetConfirm"]
  auth_password_reset_request_create: ApiSchemas["PasswordResetRequest"]
  auth_refresh_create: null
  auth_register_create: ApiSchemas["Register"]
  auth_sessions_revoke_all_create: null
  auth_sessions_revoke_others_create: null
  authoring_chapters_retrieve: null
  authoring_chapters_create: { [key: string]: JsonValue }
  authoring_chapters_destroy: null
  authoring_chapters_partial_update: { [key: string]: JsonValue }
  authoring_command_forms_retrieve: null
  authoring_content_definitions_retrieve: null
  authoring_content_definitions_create: ApiSchemas["ContentDefinitionCreateRequest"]
  authoring_content_definitions_retrieve_2: null
  authoring_content_definitions_partial_update: ApiSchemas["PatchedContentDefinitionUpdateRequest"]
  authoring_content_definitions_publish_create: null
  authoring_content_definitions_remix_create: null
  authoring_content_definitions_test_run_create: null
  authoring_content_definitions_validate_create: null
  challenge_runs_destroy: null
  challenge_runs_retrieve: null
  challenge_runs_files_destroy: null
  challenge_runs_files_partial_update: ApiSchemas["WorkspaceFile"]
  challenge_runs_files_create: ApiSchemas["WorkspaceFile"]
  challenge_runs_files_update: ApiSchemas["WorkspaceFileRename"]
  challenge_runs_retry_create: null
  challenge_runs_submit_command_create: ApiSchemas["CommandSubmit"]
  challenge_trials_runs_create: ApiSchemas["ChallengeRunStart"]
  chapters_list: null
  chapters_book_retrieve: null
  chapters_orientation_list: null
  chapters_overview_retrieve: null
  command_forms_preview_retrieve: null
  health_retrieve: null
  health_live_retrieve: null
  health_ready_retrieve: null
  orientation_lessons_retrieve: null
  orientation_lessons_complete_create: ApiSchemas["ChapterOrientationComplete"]
  player_loadout_companion_create: ApiSchemas["ShopMutationRequest"]
  player_preferences_retrieve: null
  player_preferences_partial_update: ApiSchemas["PatchedPlayerPreferences"]
  progress_dashboard_retrieve: null
  progress_stats_retrieve: null
  progress_wallet_retrieve: null
  schema_retrieve: null
  shop_catalog_retrieve: null
  shop_catalog_purchase_create: ApiSchemas["ShopMutationRequest"]
  skills_learned_retrieve: null
  stories_list: null
}

export type ApiResponseBodyByOperation = {
  admin_analytics_retrieve: ApiSchemas["AdminAnalyticsResponse"]
  admin_chapters_retrieve: ApiSchemas["AdminChapterListResponse"]
  admin_chapters_create: ApiSchemas["AdminChapter"]
  admin_chapters_partial_update: ApiSchemas["AdminChapter"]
  admin_content_retrieve: ApiSchemas["AdminContentListResponse"]
  admin_economy_adjust_create: ApiSchemas["AdminEconomyAdjustResponse"]
  admin_economy_transactions_retrieve: ApiSchemas["AdminTransactionListResponse"]
  admin_moderation_retrieve: ApiSchemas["AdminModerationListResponse"]
  admin_moderation_unpublish_create: ApiSchemas["AdminOkayResponse"]
  admin_overview_retrieve: ApiSchemas["AdminOverviewResponse"]
  admin_settings_retrieve: ApiSchemas["AdminSettingsResponse"]
  admin_settings_create: ApiSchemas["AdminFeatureFlag"]
  admin_stories_retrieve: ApiSchemas["AdminStoryListResponse"]
  admin_stories_create: ApiSchemas["AdminStory"]
  admin_stories_partial_update: ApiSchemas["AdminStory"]
  admin_users_retrieve: ApiSchemas["AdminUserListResponse"]
  admin_users_retrieve_2: ApiSchemas["AdminUserDetail"]
  admin_users_actions_create: ApiSchemas["AdminUserDetail"]
  adventure_level_tiers_runs_create: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_levels_runs_create: ApiSchemas["AdventureRunResponse"]
  adventure_runs_destroy: null
  adventure_runs_retrieve: ApiSchemas["AdventureRunResponse"]
  adventure_runs_files_destroy: ApiSchemas["AdventureRunResponse"]
  adventure_runs_files_partial_update: ApiSchemas["AdventureRunResponse"]
  adventure_runs_files_create: ApiSchemas["AdventureRunResponse"]
  adventure_runs_files_update: ApiSchemas["AdventureRunResponse"]
  adventure_runs_level_library_create: ApiSchemas["AdventureLevelLibraryResponse"]
  adventure_runs_submit_command_create: ApiSchemas["AdventureCommandResponse"]
  adventure_tier_runs_destroy: null
  adventure_tier_runs_retrieve: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_files_destroy: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_files_partial_update: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_files_create: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_files_update: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_retry_create: ApiSchemas["AdventureLevelTierRunResponse"]
  adventure_tier_runs_submit_command_create: ApiSchemas["AdventureLevelTierCommandResponse"]
  adventures_runs_create: ApiSchemas["AdventureRunResponse"]
  auth_login_create: ApiSchemas["SessionResponse"]
  auth_logout_create: null
  auth_me_retrieve: ApiSchemas["User"]
  auth_password_change_create: ApiSchemas["SessionResponse"]
  auth_password_reset_confirm_create: ApiSchemas["DetailResponse"]
  auth_password_reset_request_create: ApiSchemas["DetailResponse"]
  auth_refresh_create: ApiSchemas["AccessTokenResponse"]
  auth_register_create: ApiSchemas["RegisterResponse"]
  auth_sessions_revoke_all_create: null
  auth_sessions_revoke_others_create: ApiSchemas["DetailResponse"]
  authoring_chapters_retrieve: { [key: string]: JsonValue }
  authoring_chapters_create: { [key: string]: JsonValue }
  authoring_chapters_destroy: null
  authoring_chapters_partial_update: { [key: string]: JsonValue }
  authoring_command_forms_retrieve: { [key: string]: JsonValue }
  authoring_content_definitions_retrieve: ApiSchemas["ContentDefinitionListResponse"]
  authoring_content_definitions_create: ApiSchemas["ContentDefinition"]
  authoring_content_definitions_retrieve_2: ApiSchemas["ContentDefinition"]
  authoring_content_definitions_partial_update: ApiSchemas["ContentDefinition"]
  authoring_content_definitions_publish_create: ApiSchemas["ContentDefinition"]
  authoring_content_definitions_remix_create: ApiSchemas["ContentDefinition"]
  authoring_content_definitions_test_run_create: ApiSchemas["ContentTestRunResult"]
  authoring_content_definitions_validate_create: ApiSchemas["ContentValidationResult"]
  challenge_runs_destroy: null
  challenge_runs_retrieve: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_files_destroy: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_files_partial_update: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_files_create: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_files_update: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_retry_create: ApiSchemas["ChallengeRunResponse"]
  challenge_runs_submit_command_create: ApiSchemas["ChallengeCommandResponse"]
  challenge_trials_runs_create: ApiSchemas["ChallengeRunResponse"]
  chapters_list: Array<ApiSchemas["ChapterList"]>
  chapters_book_retrieve: { [key: string]: JsonValue }
  chapters_orientation_list: Array<ApiSchemas["ChapterOrientationLessonList"]>
  chapters_overview_retrieve: { [key: string]: JsonValue }
  command_forms_preview_retrieve: ApiSchemas["CommandFormPreviewResponse"]
  health_retrieve: { [key: string]: JsonValue }
  health_live_retrieve: { [key: string]: JsonValue }
  health_ready_retrieve: { [key: string]: JsonValue }
  orientation_lessons_retrieve: ApiSchemas["ChapterOrientationLessonDetail"]
  orientation_lessons_complete_create: ApiSchemas["ChapterOrientationLessonDetail"]
  player_loadout_companion_create: ApiSchemas["ShopEquipResponse"]
  player_preferences_retrieve: ApiSchemas["PlayerPreferences"]
  player_preferences_partial_update: ApiSchemas["PlayerPreferences"]
  progress_dashboard_retrieve: ApiSchemas["DashboardSummaryResponse"]
  progress_stats_retrieve: ApiSchemas["StatsSummaryResponse"]
  progress_wallet_retrieve: ApiSchemas["WalletSummaryResponse"]
  schema_retrieve: { [key: string]: JsonValue }
  shop_catalog_retrieve: ApiSchemas["ShopResponse"]
  shop_catalog_purchase_create: ApiSchemas["ShopPurchaseResponse"]
  skills_learned_retrieve: ApiSchemas["LearnedSkillsResponse"]
  stories_list: Array<ApiSchemas["Story"]>
}

export type ApiRequestBody<TOperation extends ApiOperationId> = ApiRequestBodyByOperation[TOperation]
export type ApiResponseBody<TOperation extends ApiOperationId> = ApiResponseBodyByOperation[TOperation]
