"""Backend and OpenAPI success-response ownership policy for Gameplay."""

from __future__ import annotations

import ast
import json

from scripts.checks.architecture_guard.contracts.gameplay_response_frontend import (
    gameplay_response_frontend_violations,
)
from scripts.checks.architecture_guard.python_analysis import (
    python_top_level_assignment_names,
    python_top_level_class_names,
)
from scripts.checks.architecture_guard.repository import (
    BACKEND,
    FRONTEND_SRC,
    PY_SUFFIXES,
    ROOT,
    TS_SUFFIXES,
    iter_files,
    rel,
)

GAMEPLAY_RESPONSE_GENERATED_OPENAPI = "frontend/src/shared/api/generated/openapi.json"


GAMEPLAY_COMMON_OPENAPI = "backend/common/openapi.py"


GAMEPLAY_ADVENTURE_OPENAPI = "backend/adventures/openapi.py"


GAMEPLAY_CHALLENGE_OPENAPI = "backend/challenges/openapi.py"


GAMEPLAY_RESPONSE_BACKEND_VIEWS = (
    "backend/adventures/views.py",
    "backend/challenges/views.py",
)


def gameplay_response_backend_violations(sources: dict[str, str]) -> list[str]:
    """Keep success-response schemas in their gameplay domain owners."""

    violations: list[str] = []
    expected_owner_classes = {
        GAMEPLAY_COMMON_OPENAPI: {
            "GameplayRunStatusField",
            "RuntimeStepResponseSerializer",
        },
        GAMEPLAY_ADVENTURE_OPENAPI: {
            "AdventureRunResponseSerializer",
            "AdventureRunPatchResponseSerializer",
            "AdventureCommandRunResponseField",
            "AdventureLevelLibraryResponseSerializer",
            "AdventureCommandResponseSerializer",
            "AdventureLevelTierRunStepResponseSerializer",
            "AdventureLevelTierCommandStepResponseSerializer",
            "AdventureLevelTierCommandRunResponseSerializer",
            "AdventureLevelTierRunResponseSerializer",
            "AdventureLevelTierCommandResponseSerializer",
        },
        GAMEPLAY_CHALLENGE_OPENAPI: {
            "ChallengeRunStepResponseSerializer",
            "ChallengeCommandStepResponseSerializer",
            "ChallengeCommandRunResponseSerializer",
            "ChallengeRunResponseSerializer",
            "ChallengeCommandResponseSerializer",
        },
    }
    owned_names = set().union(*expected_owner_classes.values())
    for owner_path, expected_names in expected_owner_classes.items():
        source = sources.get(owner_path, "")
        if not source:
            violations.append(f"{owner_path}: required gameplay response owner is missing")
            continue
        actual_names = set(python_top_level_class_names(source))
        missing_names = sorted(expected_names - actual_names)
        if missing_names:
            violations.append(
                f"{owner_path}: gameplay response owner is incomplete: {missing_names}"
            )

    for path_label, source in sorted(sources.items()):
        definitions = set(python_top_level_class_names(source)) | set(
            python_top_level_assignment_names(source)
        )
        displaced = sorted(
            name
            for name in definitions & owned_names
            if name not in expected_owner_classes.get(path_label, set())
        )
        if displaced:
            violations.append(
                f"{path_label}: displaced gameplay response owner is forbidden: "
                + ", ".join(displaced)
            )
        try:
            tree = ast.parse(source)
        except SyntaxError:
            continue
        for node in tree.body:
            if not isinstance(node, ast.ImportFrom):
                continue
            imported_names = {item.name for item in node.names}
            if path_label == GAMEPLAY_COMMON_OPENAPI and imported_names & (
                expected_owner_classes[GAMEPLAY_ADVENTURE_OPENAPI]
                | expected_owner_classes[GAMEPLAY_CHALLENGE_OPENAPI]
            ):
                violations.append(
                    f"{GAMEPLAY_COMMON_OPENAPI}: domain response re-export facades are forbidden"
                )
            domain_names = (
                expected_owner_classes[GAMEPLAY_ADVENTURE_OPENAPI]
                | expected_owner_classes[GAMEPLAY_CHALLENGE_OPENAPI]
            )
            allowed_importers = {
                GAMEPLAY_ADVENTURE_OPENAPI,
                GAMEPLAY_CHALLENGE_OPENAPI,
                *GAMEPLAY_RESPONSE_BACKEND_VIEWS,
            }
            if path_label not in allowed_importers and imported_names & domain_names:
                violations.append(
                    f"{path_label}: gameplay response import/re-export facade is forbidden"
                )

    expected_view_imports = {
        "backend/adventures/views.py": (
            "adventures.openapi",
            {
                "AdventureCommandResponseSerializer",
                "AdventureLevelLibraryResponseSerializer",
                "AdventureRunResponseSerializer",
                "AdventureLevelTierCommandResponseSerializer",
                "AdventureLevelTierRunResponseSerializer",
            },
        ),
        "backend/challenges/views.py": (
            "challenges.openapi",
            {
                "ChallengeCommandResponseSerializer",
                "ChallengeRunResponseSerializer",
            },
        ),
    }
    for view_path, (owner_module, expected_names) in expected_view_imports.items():
        source = sources.get(view_path, "")
        try:
            tree = ast.parse(source)
        except SyntaxError:
            tree = ast.Module(body=[], type_ignores=[])
        imported_from_owner = {
            item.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == owner_module
            for item in node.names
        }
        if imported_from_owner != expected_names:
            violations.append(
                f"{view_path}: response schemas must import directly from {owner_module}; "
                f"expected={sorted(expected_names)}"
            )
        imported_from_common = {
            item.name
            for node in tree.body
            if isinstance(node, ast.ImportFrom) and node.module == "common.openapi"
            for item in node.names
        }
        if imported_from_common & owned_names:
            violations.append(
                f"{view_path}: gameplay response schemas must not come from common.openapi"
            )
    return violations


def _response_schema_fields(schemas: dict, schema_name: str) -> tuple[set[str], set[str], dict]:
    component = schemas.get(schema_name, {})
    properties = component.get("properties", {}) if isinstance(component, dict) else {}
    required = component.get("required", []) if isinstance(component, dict) else []
    return set(properties), set(required), properties


def gameplay_response_openapi_violations(schema: dict) -> list[str]:
    """Require exact generated gameplay success-response shapes and references."""

    violations: list[str] = []
    schemas = schema.get("components", {}).get("schemas", {})
    exact_fields = {
        "RuntimeStepResponse": {
            "id",
            "command_text",
            "terminal_output",
            "result_category",
        },
        "AdventureRunResponse": {
            "id",
            "status",
            "replay",
            "stars",
            "library_opened",
            "is_passed",
            "selected_level",
            "next_level",
            "story",
            "chapter_id",
            "battle_stage",
            "current_level_index",
            "total_levels",
            "current_wave",
            "total_waves",
            "passed",
            "mastery",
            "completed_at",
            "current_attempt",
            "results",
            "progress",
        },
        "AdventureRunPatchResponse": {"partial", "id", "status", "current_attempt"},
        "AdventureCommandResponse": {
            "run",
            "solved",
            "stdout",
            "stderr",
            "exit_code",
            "terminal_output",
            "command_classification",
            "step",
            "command_outcome",
        },
        "AdventureLevelLibraryResponse": {"book", "run"},
        "ChallengeRunStepResponse": {
            "id",
            "command_text",
            "terminal_output",
            "result_category",
            "command_classification",
            "contextual_feedback",
            "visualization_snapshot",
            "created_at",
        },
        "ChallengeCommandStepResponse": {
            "id",
            "command_text",
            "terminal_output",
            "result_category",
            "command_classification",
            "contextual_feedback",
            "visualization_snapshot",
            "created_at",
            "evaluation_result",
        },
        "ChallengeCommandRunResponse": {
            "id",
            "replay",
            "stars",
            "status",
            "failure_reason",
            "completed_at",
            "counts",
            "repository_state",
            "visualization",
            "mastery_progress",
            "completion",
            "next_difficulty",
            "sibling_levels",
        },
        "ChallengeRunResponse": {
            "id",
            "replay",
            "stars",
            "status",
            "failure_reason",
            "completed_at",
            "challenge",
            "scenario_context",
            "chapter",
            "story",
            "battle_stage",
            "difficulty",
            "reward_coins",
            "variant",
            "mastery_progress",
            "policy",
            "counts",
            "scaffolding",
            "repository_state",
            "visualization",
            "expected_state",
            "steps",
            "next_difficulty",
            "sibling_levels",
            "completion",
        },
        "ChallengeCommandResponse": {
            "run",
            "command_outcome",
            "stdout",
            "stderr",
            "exit_code",
            "command_family",
            "diagnostic_metadata",
            "step",
        },
    }
    optional_fields = {
        "ChallengeCommandRunResponse": {
            "mastery_progress",
            "completion",
            "next_difficulty",
            "sibling_levels",
        }
    }
    for schema_name, expected_fields in exact_fields.items():
        actual_fields, required_fields, _ = _response_schema_fields(schemas, schema_name)
        expected_required = expected_fields - optional_fields.get(schema_name, set())
        component = schemas.get(schema_name, {})
        if (
            component.get("type") != "object"
            or actual_fields != expected_fields
            or required_fields != expected_required
        ):
            violations.append(
                f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: {schema_name} properties/required "
                f"must be exact"
            )

    expected_nullable = {
        "AdventureRunResponse": {
            "selected_level",
            "next_level",
            "story",
            "chapter_id",
            "battle_stage",
            "completed_at",
            "current_attempt",
        },
        "ChallengeRunResponse": {
            "failure_reason",
            "completed_at",
            "story",
            "battle_stage",
            "difficulty",
            "expected_state",
            "next_difficulty",
            "completion",
        },
        "ChallengeCommandRunResponse": {
            "failure_reason",
            "completed_at",
            "completion",
            "next_difficulty",
        },
    }
    for schema_name in exact_fields:
        nullable_fields = expected_nullable.get(schema_name, set())
        _, _, properties = _response_schema_fields(schemas, schema_name)
        actual_nullable = {
            name for name, value in properties.items() if value.get("nullable") is True
        }
        if actual_nullable != nullable_fields:
            violations.append(
                f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: {schema_name} nullable fields must be exact"
            )

    expected_status = {
        "type": "string",
        "enum": ["started", "completed", "failed", "abandoned"],
    }
    if schemas.get("GameplayRunStatus") != expected_status:
        violations.append(
            f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: GameplayRunStatus must be one exact shared enum"
        )
    if schemas.get("PartialEnum", {}).get("type") != "boolean" or schemas.get(
        "PartialEnum", {}
    ).get("enum") != [True]:
        violations.append(
            f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: PartialEnum must be the literal true branch"
        )
    expected_union = {
        "oneOf": [
            {"$ref": "#/components/schemas/AdventureRunResponse"},
            {"$ref": "#/components/schemas/AdventureRunPatchResponse"},
        ]
    }
    if schemas.get("AdventureCommandRunResponse") != expected_union:
        violations.append(
            f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: AdventureCommandRunResponse must be the exact full/patch union"
        )
    expected_component_refs = {
        ("AdventureCommandResponse", "run"): "AdventureCommandRunResponse",
        ("AdventureCommandResponse", "step"): "RuntimeStepResponse",
        ("AdventureLevelLibraryResponse", "run"): "AdventureRunResponse",
        ("ChallengeRunResponse", "steps"): "ChallengeRunStepResponse",
        ("ChallengeCommandResponse", "run"): "ChallengeCommandRunResponse",
        ("ChallengeCommandResponse", "step"): "ChallengeCommandStepResponse",
    }
    for (schema_name, field_name), expected_ref in expected_component_refs.items():
        field_schema = schemas.get(schema_name, {}).get("properties", {}).get(field_name, {})
        if field_name == "steps":
            field_schema = field_schema.get("items", {})
        if field_schema != {"$ref": f"#/components/schemas/{expected_ref}"}:
            violations.append(
                f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: {schema_name}.{field_name} must reference {expected_ref}"
            )
    for schema_name in (
        "AdventureRunResponse",
        "AdventureRunPatchResponse",
        "ChallengeRunResponse",
        "ChallengeCommandRunResponse",
    ):
        status_schema = schemas.get(schema_name, {}).get("properties", {}).get("status")
        if status_schema != {"$ref": "#/components/schemas/GameplayRunStatus"}:
            violations.append(
                f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: {schema_name}.status must reference GameplayRunStatus"
            )

    response_refs = {
        (
            "/api/adventure-levels/{level_id}/runs/",
            "post",
            "201",
        ): "AdventureRunResponse",
        (
            "/api/adventures/{adventure_slug}/runs/",
            "post",
            "201",
        ): "AdventureRunResponse",
        ("/api/adventure-runs/{run_id}/", "get", "200"): "AdventureRunResponse",
        (
            "/api/adventure-runs/{run_id}/level-library/",
            "post",
            "200",
        ): "AdventureLevelLibraryResponse",
        (
            "/api/adventure-runs/{run_id}/submit-command/",
            "post",
            "200",
        ): "AdventureCommandResponse",
        (
            "/api/challenge-trials/{trial_id}/runs/",
            "post",
            "201",
        ): "ChallengeRunResponse",
        ("/api/challenge-runs/{run_id}/retry/", "post", "201"): "ChallengeRunResponse",
        ("/api/challenge-runs/{run_id}/", "get", "200"): "ChallengeRunResponse",
        (
            "/api/challenge-runs/{run_id}/submit-command/",
            "post",
            "200",
        ): "ChallengeCommandResponse",
    }
    for prefix, component in (
        ("adventure-runs", "AdventureRunResponse"),
        ("challenge-runs", "ChallengeRunResponse"),
    ):
        for method in ("post", "patch", "put", "delete"):
            response_refs[(f"/api/{prefix}/{{run_id}}/files/", method, "200")] = component
    for (path, method, status), component in response_refs.items():
        actual = (
            schema.get("paths", {})
            .get(path, {})
            .get(method, {})
            .get("responses", {})
            .get(status, {})
            .get("content", {})
            .get("application/json", {})
            .get("schema")
        )
        if actual != {"$ref": f"#/components/schemas/{component}"}:
            violations.append(
                f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: {method.upper()} {path} {status} must return {component}"
            )
    return violations


def check_gameplay_response_contract_ownership() -> list[str]:
    """Keep gameplay success responses domain-owned, exact, and generated-derived."""

    backend_sources = {
        rel(path): path.read_text(encoding="utf-8", errors="ignore")
        for path in iter_files(BACKEND, PY_SUFFIXES)
        if not any(part in {"migrations", "tests"} for part in path.parts)
        and not path.name.startswith("test_")
    }
    violations = gameplay_response_backend_violations(backend_sources)

    frontend_sources = {
        rel(path): path.read_text(encoding="utf-8", errors="ignore")
        for path in iter_files(FRONTEND_SRC, TS_SUFFIXES)
    }
    violations.extend(gameplay_response_frontend_violations(frontend_sources))
    try:
        schema = json.loads(
            (ROOT / GAMEPLAY_RESPONSE_GENERATED_OPENAPI).read_text(encoding="utf-8")
        )
    except (json.JSONDecodeError, OSError) as error:
        violations.append(
            f"{GAMEPLAY_RESPONSE_GENERATED_OPENAPI}: invalid generated schema: {error}"
        )
    else:
        violations.extend(gameplay_response_openapi_violations(schema))
    return violations
