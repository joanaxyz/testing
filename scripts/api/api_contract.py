#!/usr/bin/env python3
"""Generate the committed frontend API contract from the DRF OpenAPI schema.

This intentionally uses only the Python standard library so CI does not need a
Node code generator before the app can verify backend/frontend contract drift.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
BACKEND = ROOT / "backend"
GENERATED = ROOT / "frontend" / "src" / "shared" / "api" / "generated"
OPENAPI_JSON = GENERATED / "openapi.json"
API_TYPES_TS = GENERATED / "apiTypes.ts"
HTTP_METHODS = {"get", "post", "put", "patch", "delete", "head", "options"}
NO_BODY_SUCCESS_ALLOWLIST: set[str] = set()

REQUIRED_OPERATION_RESPONSES = {
    "ai_chat_create": "AIChatResponse",
    "admin_analytics_retrieve": "AdminAnalyticsResponse",
    "admin_chapters_retrieve": "AdminChapterListResponse",
    "admin_chapters_create": "AdminChapter",
    "admin_chapters_partial_update": "AdminChapter",
    "admin_content_retrieve": "AdminContentListResponse",
    "admin_economy_adjust_create": "AdminEconomyAdjustResponse",
    "admin_economy_transactions_retrieve": "AdminTransactionListResponse",
    "admin_moderation_retrieve": "AdminModerationListResponse",
    "admin_moderation_unpublish_create": "AdminOkayResponse",
    "admin_overview_retrieve": "AdminOverviewResponse",
    "admin_settings_retrieve": "AdminSettingsResponse",
    "admin_settings_create": "AdminFeatureFlag",
    "admin_stories_retrieve": "AdminStoryListResponse",
    "admin_stories_create": "AdminStory",
    "admin_stories_partial_update": "AdminStory",
    "admin_users_retrieve": "AdminUserListResponse",
    "admin_users_retrieve_2": "AdminUserDetail",
    "admin_users_actions_create": "AdminUserDetail",
    "authoring_content_definitions_retrieve": "ContentDefinitionListResponse",
    "authoring_content_definitions_create": "ContentDefinition",
    "authoring_content_definitions_retrieve_2": "ContentDefinition",
    "authoring_content_definitions_partial_update": "ContentDefinition",
    "authoring_content_definitions_publish_create": "ContentDefinition",
    "authoring_content_definitions_remix_create": "ContentDefinition",
    "authoring_content_definitions_test_run_create": "ContentTestRunResult",
    "authoring_content_definitions_validate_create": "ContentValidationResult",
    "adventure_levels_runs_create": "AdventureRunResponse",
    "adventure_runs_retrieve": "AdventureRunResponse",
    "adventure_runs_files_create": "AdventureRunResponse",
    "adventure_runs_files_partial_update": "AdventureRunResponse",
    "adventure_runs_level_library_create": "AdventureLevelLibraryResponse",
    "adventure_runs_submit_command_create": "AdventureCommandResponse",
    "challenge_trials_runs_create": "ChallengeRunResponse",
    "challenge_runs_retrieve": "ChallengeRunResponse",
    "challenge_runs_retry_create": "ChallengeRunResponse",
    "challenge_runs_files_create": "ChallengeRunResponse",
    "challenge_runs_files_partial_update": "ChallengeRunResponse",
    "challenge_runs_submit_command_create": "ChallengeCommandResponse",
    "progress_dashboard_retrieve": "DashboardSummaryResponse",
    "progress_stats_retrieve": "StatsSummaryResponse",
    "progress_wallet_retrieve": "WalletSummaryResponse",
    "shop_catalog_retrieve": "ShopResponse",
    "shop_catalog_purchase_create": "ShopPurchaseResponse",
    "player_loadout_companion_create": "ShopEquipResponse",
    "skills_learned_retrieve": "LearnedSkillsResponse",
    "command_forms_preview_retrieve": "CommandFormPreviewResponse",
}

HEADER = """// GENERATED FILE. DO NOT EDIT.\n// Source: backend DRF/drf-spectacular OpenAPI schema.\n// Regenerate with: python scripts/generate_api_contract.py\n\n"""


def backend_python() -> Path:
    """Use the repository virtualenv when the caller is outside it."""
    candidates = (
        BACKEND / ".venv" / "Scripts" / "python.exe",
        BACKEND / ".venv" / "bin" / "python",
    )
    current = Path(sys.executable).resolve()
    for candidate in candidates:
        if candidate.is_file() and candidate.resolve() != current:
            return candidate
    return current


def contract_env() -> dict[str, str]:
    env = os.environ.copy()
    env.setdefault("DJANGO_SETTINGS_MODULE", "config.test_settings")
    env.setdefault("DJANGO_DEBUG", "True")
    env.setdefault("DJANGO_SECRET_KEY", "dev-contract-generation-secret")
    env.setdefault("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver")
    env.setdefault("REDIS_URL", "redis://localhost:6379/0")
    return env


def generate_openapi_json(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            str(backend_python()),
            "manage.py",
            "spectacular",
            "--file",
            str(path),
            "--format",
            "openapi-json",
            "--validate",
        ],
        cwd=BACKEND,
        env=contract_env(),
        text=True,
        capture_output=True,
    )
    if result.returncode != 0:
        sys.stderr.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise SystemExit(result.returncode)
    if not path.exists() or path.stat().st_size == 0:
        raise SystemExit("OpenAPI generation produced no schema output.")


def ts_string(value: str) -> str:
    return json.dumps(value)


def operation_key(operation_id: str, method: str, path: str) -> str:
    if operation_id:
        key = re.sub(r"[^A-Za-z0-9_$]", "_", operation_id)
    else:
        key = f"{method}_{path.strip('/').replace('/', '_').replace('{', '').replace('}', '')}"
        key = re.sub(r"[^A-Za-z0-9_$]", "_", key)
    if not key or key[0].isdigit():
        key = f"operation_{key}"
    return key


def collect_operations(schema: dict[str, Any]) -> list[dict[str, Any]]:
    operations: list[dict[str, Any]] = []
    for path in sorted(schema.get("paths", {})):
        path_item = schema["paths"][path]
        if not isinstance(path_item, dict):
            continue
        for method in sorted(path_item):
            if method not in HTTP_METHODS:
                continue
            operation = path_item.get(method) or {}
            operation_id = str(operation.get("operationId") or "")
            key = operation_key(operation_id, method, path)
            operations.append(
                {
                    "key": key,
                    "operationId": operation_id,
                    "method": method.upper(),
                    "path": path,
                    "tags": operation.get("tags") or [],
                }
            )
    return operations


def schema_ref_name(ref: str) -> str:
    return ref.rsplit("/", 1)[-1]


def ts_identifier(name: str) -> str:
    key = re.sub(r"[^A-Za-z0-9_$]", "_", name)
    if not key or key[0].isdigit():
        key = f"Schema_{key}"
    return key


def schema_to_ts(schema: Any, *, seen: set[int] | None = None) -> str:
    if not isinstance(schema, dict):
        return "JsonValue"
    if schema.get("nullable") is True:
        return f"{schema_to_ts({key: value for key, value in schema.items() if key != 'nullable'}, seen=seen)} | null"
    if schema.get("nullable") is True:
        return f"{schema_to_ts({key: value for key, value in schema.items() if key != 'nullable'}, seen=seen)} | null"
    if "$ref" in schema:
        return f"ApiSchemas[{ts_string(schema_ref_name(str(schema['$ref'])))}]"
    if seen is None:
        seen = set()
    identity = id(schema)
    if identity in seen:
        return "JsonValue"
    seen.add(identity)
    for key in ("oneOf", "anyOf"):
        variants = schema.get(key)
        if isinstance(variants, list) and variants:
            return " | ".join(schema_to_ts(item, seen=seen.copy()) for item in variants)
    variants = schema.get("allOf")
    if isinstance(variants, list) and variants:
        return " & ".join(schema_to_ts(item, seen=seen.copy()) for item in variants)
    enum = schema.get("enum")
    if isinstance(enum, list) and enum:
        return " | ".join(json.dumps(item) for item in enum)
    schema_type = schema.get("type")
    if isinstance(schema_type, list):
        return " | ".join(
            schema_to_ts({**schema, "type": item}, seen=seen.copy()) for item in schema_type
        )
    if schema_type in {"integer", "number"}:
        return "number"
    if schema_type == "string":
        return "string"
    if schema_type == "boolean":
        return "boolean"
    if schema_type == "null":
        return "null"
    if schema_type == "array":
        return f"Array<{schema_to_ts(schema.get('items') or {}, seen=seen.copy())}>"
    if schema_type == "object" or "properties" in schema or "additionalProperties" in schema:
        properties = schema.get("properties") or {}
        required = set(schema.get("required") or [])
        parts: list[str] = []
        if isinstance(properties, dict):
            for name, subschema in sorted(properties.items()):
                optional = "" if name in required else "?"
                parts.append(
                    f"{ts_string(name)}{optional}: {schema_to_ts(subschema, seen=seen.copy())}"
                )
        additional = schema.get("additionalProperties")
        if additional is True:
            parts.append("[key: string]: JsonValue")
        elif isinstance(additional, dict):
            parts.append(f"[key: string]: {schema_to_ts(additional, seen=seen.copy())}")
        if not parts:
            return "JsonObject"
        return "{ " + "; ".join(parts) + " }"
    return "JsonValue"


def first_json_schema(content: Any) -> dict[str, Any] | None:
    if not isinstance(content, dict):
        return None
    for content_type in ("application/json", "application/*+json", "*/*"):
        item = content.get(content_type)
        if isinstance(item, dict) and isinstance(item.get("schema"), dict):
            return item["schema"]
    for item in content.values():
        if isinstance(item, dict) and isinstance(item.get("schema"), dict):
            return item["schema"]
    return None


def operation_request_ts(operation: dict[str, Any]) -> str:
    request_body = operation.get("requestBody") or {}
    schema = first_json_schema(request_body.get("content"))
    return schema_to_ts(schema) if schema is not None else "null"


def operation_response_ts(operation: dict[str, Any]) -> str:
    responses = operation.get("responses") or {}
    for status_code in sorted(responses):
        if not str(status_code).startswith("2"):
            continue
        response = responses.get(status_code) or {}
        schema = first_json_schema(response.get("content"))
        if schema is not None:
            return schema_to_ts(schema)
        if str(status_code) == "204":
            return "null"
    return "JsonValue"


def undocumented_success_responses(schema: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    for path, path_item in sorted((schema.get("paths") or {}).items()):
        if not isinstance(path_item, dict):
            continue
        for method, operation in sorted(path_item.items()):
            if method not in HTTP_METHODS or not isinstance(operation, dict):
                continue
            responses = operation.get("responses") or {}
            for status_code, response in sorted(responses.items()):
                if not str(status_code).startswith("2") or str(status_code) == "204":
                    continue
                operation_key_label = f"{method.upper()} {path} {status_code}"
                if operation_key_label in NO_BODY_SUCCESS_ALLOWLIST:
                    continue
                if first_json_schema((response or {}).get("content")) is None:
                    missing.append(operation_key_label)
    return missing


def schema_component_name(schema: dict[str, Any] | None) -> str | None:
    if not isinstance(schema, dict):
        return None
    if "$ref" in schema:
        return schema_ref_name(str(schema["$ref"]))
    return None


def required_operation_response_mismatches(schema: dict[str, Any]) -> list[str]:
    mismatches: list[str] = []
    operation_map = {op["key"]: op for op in collect_operations(schema)}
    for operation_id, expected_component in sorted(REQUIRED_OPERATION_RESPONSES.items()):
        op = operation_map.get(operation_id)
        if op is None:
            mismatches.append(f"{operation_id}: operation missing from OpenAPI schema")
            continue
        operation = schema["paths"][op["path"]][op["method"].lower()]
        actual_component = None
        responses = operation.get("responses") or {}
        for status_code in sorted(responses):
            if not str(status_code).startswith("2"):
                continue
            actual_component = schema_component_name(
                first_json_schema((responses[status_code] or {}).get("content"))
            )
            if actual_component:
                break
        if actual_component != expected_component:
            mismatches.append(
                f"{operation_id}: expected {expected_component}, got {actual_component or 'no component response'}"
            )
    return mismatches


def write_api_types(schema_path: Path, out_path: Path) -> None:
    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    operations = collect_operations(schema)
    path_literals = sorted({op["path"] for op in operations})
    methods_by_path: dict[str, list[str]] = {}
    request_by_operation: dict[str, str] = {}
    response_by_operation: dict[str, str] = {}
    operation_by_key: dict[str, dict[str, Any]] = {}
    for op in operations:
        methods_by_path.setdefault(op["path"], []).append(op["method"])
        operation = schema["paths"][op["path"]][op["method"].lower()]
        request_by_operation[op["key"]] = operation_request_ts(operation)
        response_by_operation[op["key"]] = operation_response_ts(operation)
        operation_by_key[op["key"]] = operation
    schemas = schema.get("components", {}).get("schemas", {}) or {}
    lines: list[str] = [HEADER]
    lines.append("export type JsonPrimitive = string | number | boolean | null\n")
    lines.append("export type JsonValue = JsonPrimitive | JsonObject | JsonValue[]\n")
    lines.append("export type JsonObject = { [key: string]: JsonValue }\n\n")
    lines.append("export type ApiSchemas = {\n")
    if schemas:
        for name, schema_def in sorted(schemas.items()):
            lines.append(f"  {ts_string(name)}: {schema_to_ts(schema_def)}\n")
    else:
        lines.append("  [key: string]: JsonValue\n")
    lines.append("}\n\n")
    lines.append("export type ApiPath =\n")
    if path_literals:
        for path in path_literals:
            lines.append(f"  | {ts_string(path)}\n")
    else:
        lines.append("  | never\n")
    lines.append("\n")
    lines.append(
        "export type ApiMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE' | 'HEAD' | 'OPTIONS'\n\n"
    )
    lines.append("export type ApiMethodByPath = {\n")
    for path in path_literals:
        methods = " | ".join(ts_string(method) for method in sorted(set(methods_by_path[path])))
        lines.append(f"  {ts_string(path)}: {methods}\n")
    lines.append("}\n\n")
    lines.append("export const apiOperations = {\n")
    seen: set[str] = set()
    unique_ops: list[dict[str, Any]] = []
    for op in operations:
        key = op["key"]
        base = key
        counter = 2
        while key in seen:
            key = f"{base}_{counter}"
            counter += 1
        seen.add(key)
        op = {**op, "key": key}
        unique_ops.append(op)
        tags = json.dumps(op["tags"])
        lines.append(
            f"  {key}: {{ method: {ts_string(op['method'])}, path: {ts_string(op['path'])}, operationId: {ts_string(op['operationId'])}, tags: {tags} }},\n"
        )
    lines.append("} as const\n\n")
    lines.append("export type ApiOperationId = keyof typeof apiOperations\n")
    lines.append("export type ApiOperation = (typeof apiOperations)[ApiOperationId]\n\n")
    lines.append("export type ApiRequestBodyByOperation = {\n")
    for op in unique_ops:
        lines.append(f"  {op['key']}: {request_by_operation.get(op['key'], 'null')}\n")
    lines.append("}\n\n")
    lines.append("export type ApiResponseBodyByOperation = {\n")
    for op in unique_ops:
        lines.append(f"  {op['key']}: {response_by_operation.get(op['key'], 'JsonValue')}\n")
    lines.append("}\n\n")
    lines.append(
        "export type ApiRequestBody<TOperation extends ApiOperationId> = ApiRequestBodyByOperation[TOperation]\n"
    )
    lines.append(
        "export type ApiResponseBody<TOperation extends ApiOperationId> = ApiResponseBodyByOperation[TOperation]\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text("".join(lines), encoding="utf-8")


def generate_contract(openapi_path: Path = OPENAPI_JSON, types_path: Path = API_TYPES_TS) -> None:
    generate_openapi_json(openapi_path)
    write_api_types(openapi_path, types_path)


def check_contract() -> int:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        expected_schema = tmpdir / "openapi.json"
        expected_types = tmpdir / "apiTypes.ts"
        generate_contract(expected_schema, expected_types)
        generated_schema = json.loads(expected_schema.read_text(encoding="utf-8"))
        undocumented = undocumented_success_responses(generated_schema)
        if undocumented:
            print("OpenAPI success responses without a JSON schema:", file=sys.stderr)
            for item in undocumented:
                print(f"  {item}", file=sys.stderr)
            print(
                "Add extend_schema(... responses=...) annotations before regenerating.",
                file=sys.stderr,
            )
            return 1
        contract_mismatches = required_operation_response_mismatches(generated_schema)
        if contract_mismatches:
            print(
                "Critical API operations are missing their named response components:",
                file=sys.stderr,
            )
            for item in contract_mismatches:
                print(f"  {item}", file=sys.stderr)
            print(
                "Add or fix extend_schema(... responses=...) annotations before regenerating.",
                file=sys.stderr,
            )
            return 1
        expected = {
            OPENAPI_JSON: expected_schema.read_text(encoding="utf-8"),
            API_TYPES_TS: expected_types.read_text(encoding="utf-8"),
        }
        missing = [path for path in expected if not path.exists()]
        if missing:
            for path in missing:
                print(
                    f"Missing generated API contract file: {path.relative_to(ROOT)}",
                    file=sys.stderr,
                )
            print("Run: python scripts/generate_api_contract.py", file=sys.stderr)
            return 1
        stale = [
            path for path, text in expected.items() if path.read_text(encoding="utf-8") != text
        ]
        if stale:
            for path in stale:
                print(
                    f"Stale generated API contract file: {path.relative_to(ROOT)}", file=sys.stderr
                )
            print("Run: python scripts/generate_api_contract.py", file=sys.stderr)
            return 1
    print("Generated API contract is current.")
    return 0
