from django.db import OperationalError, transaction
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from adventures.models import (
    AdventureLevel,
    AdventureLevelTier,
    AdventureLevelTierRun,
    AdventureRun,
)
from adventures.openapi import (
    AdventureCommandResponseSerializer,
    AdventureLevelLibraryResponseSerializer,
    AdventureLevelTierCommandResponseSerializer,
    AdventureLevelTierRunResponseSerializer,
    AdventureRunResponseSerializer,
)
from adventures.payloads import (
    adventure_command_payload,
    adventure_level_library_payload,
    adventure_run_payload,
)
from adventures.services import (
    AdventureCommandService,
    AdventureLevelTierCommandProcessingService,
    AdventureLevelTierRunService,
    AdventureRunService,
)
from adventures.tier_payloads import (
    command_run_payload,
    prefetch_run_payload_context,
    tier_run_payload,
)
from adventures.tier_serializers import AdventureLevelTierRunStartSerializer
from common.constants import SESSION_STATUS_STARTED
from common.exceptions import Conflict, Locked
from common.schemas.openapi import RequiredPatchBodyAutoSchema
from common.serializers import (
    CommandSubmitSerializer,
    WorkspaceFilePathSerializer,
    WorkspaceFileRenameSerializer,
    WorkspaceFileSerializer,
)
from common.services.run_workspace import RunWorkspaceFileService
from curriculum.selectors import adventure_locked, chapter_locked, level_locked
from players.services import get_or_create_player

ADVENTURE_WORKSPACE_FILES = RunWorkspaceFileService(ended_message="This attempt has already ended.")
ADVENTURE_TIER_WORKSPACE_FILES = RunWorkspaceFileService(
    ended_message="This adventure tier run has already ended."
)


def _get_run(run_id: int, player) -> AdventureRun:
    return (
        AdventureRun.objects.select_related(
            "level",
            "level__chapter",
            "level__chapter__story",
            "level__source_content_definition",
            "current_wave",
            "selected_variant",
        )
        .prefetch_related("level__command_forms", "level__waves", "current_wave__command_forms")
        .get(id=run_id, player=player)
    )


def _run_with_active_attempt(
    run_id: int,
    player,
    *,
    lock: bool = False,
) -> tuple[AdventureRun, AdventureRun]:
    queryset = (
        AdventureRun.objects.select_related(
            "level",
            "level__chapter",
            "level__chapter__story",
            "level__source_content_definition",
            "current_wave",
            "selected_variant",
        )
        .prefetch_related("level__command_forms", "level__waves", "current_wave__command_forms")
        .filter(id=run_id, player=player, status=SESSION_STATUS_STARTED)
    )
    if lock:
        queryset = queryset.select_for_update(nowait=True, of=("self",))
    attempt = queryset.first()
    if attempt is None:
        _get_run(run_id, player)
        raise Locked("This run has no active attempt.")
    return attempt, attempt


def _assert_level_unlocked(player, level: AdventureLevel) -> None:
    from shop.access import require_companion

    require_companion(player)
    chapter = level.chapter
    if chapter.story_id:
        from curriculum.selectors import story_locked

        locked, reason = story_locked(player=player, story=chapter.story)
        if locked:
            raise Locked(reason or "This story is locked.")
    locked, reason = chapter_locked(player=player, chapter=chapter)
    if locked:
        raise Locked(reason or "Clear the previous chapter to unlock this adventure.")
    locked, reason = adventure_locked(player=player, adventure=level)
    if locked:
        raise Locked(reason or "Complete the previous adventure to unlock this adventure.")
    locked, reason = level_locked(player=player, level=level)
    if locked:
        raise Locked(reason or "Complete the previous level to unlock this one.")
    if level.source_content_definition_id:
        from shop.access import can_launch

        if not can_launch(player.user, level.source_content_definition):
            raise PermissionDenied("You do not have access to this adventure.")


class AdventureLevelRunStartAPIView(APIView):
    @extend_schema(request=None, responses={201: AdventureRunResponseSerializer})
    def post(self, request, level_id: int):
        level = (
            AdventureLevel.objects.select_related(
                "chapter",
                "chapter__story",
                "source_content_definition",
            )
            .prefetch_related("command_forms", "waves", "waves__variants")
            .get(id=level_id, is_published=True)
        )
        player = get_or_create_player(request.user)
        _assert_level_unlocked(player, level)
        run = AdventureRunService().start_run(
            player=player,
            level=level,
        )
        return Response(adventure_run_payload(run), status=201)


class AdventureRunStartAPIView(APIView):
    @extend_schema(request=None, responses={201: AdventureRunResponseSerializer})
    def post(self, request, adventure_slug: str):
        raise ValidationError(
            {
                "detail": (
                    "Adventure runs must start from a level: "
                    "/api/adventure-levels/{level_id}/runs/."
                )
            }
        )


class AdventureRunDetailAPIView(APIView):
    @extend_schema(responses={200: AdventureRunResponseSerializer})
    def get(self, request, run_id: int):
        run = _get_run(run_id, get_or_create_player(request.user))
        return Response(adventure_run_payload(run))

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, run_id: int):
        player = get_or_create_player(request.user)
        run = AdventureRun.objects.filter(id=run_id, player=player).first()
        if run is not None:
            AdventureRunService().discard(run=run)
        return Response(status=204)


class AdventureRunSubmitCommandAPIView(APIView):
    throttle_scope = "command_submit"

    @extend_schema(
        request=CommandSubmitSerializer, responses={200: AdventureCommandResponseSerializer}
    )
    @transaction.atomic
    def post(self, request, run_id: int):
        serializer = CommandSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        player = get_or_create_player(request.user)
        try:
            run, attempt = _run_with_active_attempt(run_id, player, lock=True)
        except OperationalError as exc:
            raise Conflict(
                "This command is still being processed - try again in a moment."
            ) from exc
        result = AdventureCommandService().submit(
            attempt=attempt,
            command=serializer.validated_data["command"],
            execution=serializer.validated_data["execution"],
        )
        submitted_attempt = result["attempt"]
        # A wave clear that advances to the next wave keeps the run STARTED but
        # still swaps in a fresh problem, so reload the full run payload too.
        transitioned = (
            run.status != SESSION_STATUS_STARTED
            or submitted_attempt.status != SESSION_STATUS_STARTED
            or result.get("run_transitioned", False)
        )
        run_payload = (
            adventure_run_payload(run, include_current_steps=False)
            if transitioned
            else adventure_command_payload(
                run,
                attempt=submitted_attempt,
                repository_state=result["repository_state"],
                executed_commands=result["executed_commands"],
            )
        )
        step = result["step"]
        return Response(
            {
                "run": run_payload,
                "solved": result["solved"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "terminal_output": result["terminal_output"],
                "command_classification": result["command_classification"],
                "command_outcome": result["command_outcome"],
                "step": {
                    "id": step.id,
                    "command_text": step.command_text,
                    "terminal_output": step.terminal_output,
                    "result_category": step.result_category,
                },
            }
        )


class AdventureRunLevelLibraryAPIView(APIView):
    @extend_schema(request=None, responses={200: AdventureLevelLibraryResponseSerializer})
    @transaction.atomic
    def post(self, request, run_id: int):
        try:
            run, _attempt = _run_with_active_attempt(
                run_id, get_or_create_player(request.user), lock=True
            )
        except OperationalError as exc:
            raise Conflict(
                "This command is still being processed - try again in a moment."
            ) from exc
        book = adventure_level_library_payload(run)
        if book is None:
            raise NotFound("This adventure level has no command library.")
        AdventureRunService().record_library_opened(run=run)
        return Response({"book": book, "run": adventure_run_payload(run)})


class AdventureWorkspaceFileAPIView(APIView):
    throttle_scope = "command_submit"
    schema = RequiredPatchBodyAutoSchema()

    @extend_schema(request=WorkspaceFileSerializer, responses={200: AdventureRunResponseSerializer})
    def post(self, request, run_id: int):
        return self._mutate_file(request, run_id, ADVENTURE_WORKSPACE_FILES.create_file)

    @extend_schema(
        request={"application/json": {"$ref": "#/components/schemas/WorkspaceFile"}},
        responses={200: AdventureRunResponseSerializer},
    )
    def patch(self, request, run_id: int):
        return self._mutate_file(request, run_id, ADVENTURE_WORKSPACE_FILES.write_file)

    @extend_schema(
        request=WorkspaceFileRenameSerializer, responses={200: AdventureRunResponseSerializer}
    )
    def put(self, request, run_id: int):
        serializer = WorkspaceFileRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run, attempt = _run_with_active_attempt(run_id, get_or_create_player(request.user))
        updated = ADVENTURE_WORKSPACE_FILES.rename_file(
            run=attempt,
            path=serializer.validated_data["path"],
            new_path=serializer.validated_data["new_path"],
        )
        run.repository_state = updated.repository_state
        return Response(adventure_run_payload(run))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="path",
                type={"type": "string", "maxLength": 240},
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={200: AdventureRunResponseSerializer},
    )
    def delete(self, request, run_id: int):
        serializer = WorkspaceFilePathSerializer(data=request.data or request.query_params)
        serializer.is_valid(raise_exception=True)
        run, attempt = _run_with_active_attempt(run_id, get_or_create_player(request.user))
        updated = ADVENTURE_WORKSPACE_FILES.delete_file(
            run=attempt,
            path=serializer.validated_data["path"],
        )
        run.repository_state = updated.repository_state
        return Response(adventure_run_payload(run))

    def _mutate_file(self, request, run_id: int, mutate):
        serializer = WorkspaceFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run, attempt = _run_with_active_attempt(run_id, get_or_create_player(request.user))
        updated = mutate(
            run=attempt,
            path=serializer.validated_data["path"],
            content=serializer.validated_data.get("content", ""),
        )
        run.repository_state = updated.repository_state
        return Response(adventure_run_payload(run))


# ---------------------------------------------------------------------------
# AdventureLevelTierRun lifecycle - mirrors challenges/views.py exactly,
# new/parallel code only. Nothing above this line was modified.
# ---------------------------------------------------------------------------


class AdventureLevelTierRunStartAPIView(APIView):
    @extend_schema(
        request=AdventureLevelTierRunStartSerializer,
        responses={201: AdventureLevelTierRunResponseSerializer},
    )
    def post(self, request, tier_id: int):
        serializer = AdventureLevelTierRunStartSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        tier = AdventureLevelTier.objects.select_related(
            "adventure_level",
            "adventure_level__chapter",
            "adventure_level__chapter__story",
        ).get(id=tier_id, is_published=True)
        player = get_or_create_player(request.user)
        chapter = tier.adventure_level.chapter
        if chapter.story_id:
            from curriculum.selectors import story_locked

            locked, reason = story_locked(player=player, story=chapter.story)
            if locked:
                raise Locked(reason or "This story is locked.")
            locked, reason = chapter_locked(player=player, chapter=chapter)
            if locked:
                raise Locked(reason or "This chapter is locked.")
        prior_run = None
        prior_run_id = serializer.validated_data.get("prior_run_id")
        if prior_run_id:
            prior_run = AdventureLevelTierRun.objects.get(id=prior_run_id, player=player)
        is_replay = bool(serializer.validated_data.get("replay"))
        run = AdventureLevelTierRunService().start_run(
            player=player,
            tier=tier,
            source_entry_point=serializer.validated_data["source_entry_point"],
            prior_run=prior_run,
            is_replay=is_replay,
        )
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run), status=201)


class AdventureLevelTierRunDetailAPIView(APIView):
    @extend_schema(responses={200: AdventureLevelTierRunResponseSerializer})
    def get(self, request, run_id: int):
        run = AdventureLevelTierRunService.hydrate_run(
            run_id, player=get_or_create_player(request.user)
        )
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run))

    @extend_schema(request=None, responses={204: None})
    def delete(self, request, run_id: int):
        player = get_or_create_player(request.user)
        run = AdventureLevelTierRun.objects.filter(id=run_id, player=player).first()
        if run is not None:
            AdventureLevelTierRunService().discard(run=run)
        return Response(status=204)


class AdventureLevelTierCommandSubmitAPIView(APIView):
    throttle_scope = "command_submit"

    @extend_schema(
        request=CommandSubmitSerializer,
        responses={200: AdventureLevelTierCommandResponseSerializer},
    )
    @transaction.atomic
    def post(self, request, run_id: int):
        serializer = CommandSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        player = get_or_create_player(request.user)
        try:
            run = (
                AdventureLevelTierRun.objects.select_for_update(nowait=True, of=("self",))
                .select_related(
                    "tier__adventure_level__chapter__story",
                    "tier__adventure_level__chapter",
                    "current_wave",
                    "selected_variant",
                )
                .get(id=run_id, player=player)
            )
        except OperationalError as exc:
            raise Conflict(
                "This command is still being processed - try again in a moment."
            ) from exc
        result = AdventureLevelTierCommandProcessingService().submit_command(
            run=run,
            command=serializer.validated_data["command"],
            execution=serializer.validated_data["execution"],
        )
        if result["run"].status != SESSION_STATUS_STARTED:
            prefetch_run_payload_context(result["run"])
        payload = command_run_payload(
            result["run"],
            repository_state=result["repository_state"],
            visualization=result["visualization"],
        )
        return Response(
            {
                "run": payload,
                "command_outcome": result["command_outcome"],
                "stdout": result["stdout"],
                "stderr": result["stderr"],
                "exit_code": result["exit_code"],
                "command_family": result["command_family"],
                "diagnostic_metadata": result["diagnostic_metadata"],
                "step": {
                    "id": result["step"].id,
                    "command_text": result["step"].command_text,
                    "terminal_output": result["terminal_output"],
                    "result_category": result["step"].result_category,
                    "evaluation_result": result["evaluation_result"],
                    "command_classification": result["command_classification"],
                    "contextual_feedback": result["contextual_feedback"],
                    "visualization_snapshot": result["visualization"],
                    "created_at": result["step"].created_at,
                },
            }
        )


class AdventureLevelTierWorkspaceFileAPIView(APIView):
    throttle_scope = "command_submit"
    schema = RequiredPatchBodyAutoSchema()

    @extend_schema(
        request=WorkspaceFileSerializer, responses={200: AdventureLevelTierRunResponseSerializer}
    )
    def post(self, request, run_id: int):
        serializer = WorkspaceFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = _get_tier_workspace_run(run_id, get_or_create_player(request.user))
        run = ADVENTURE_TIER_WORKSPACE_FILES.create_file(
            run=run,
            path=serializer.validated_data["path"],
            content=serializer.validated_data.get("content", ""),
        )
        run = AdventureLevelTierRunService.hydrate_run(run)
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run))

    @extend_schema(
        request={"application/json": {"$ref": "#/components/schemas/WorkspaceFile"}},
        responses={200: AdventureLevelTierRunResponseSerializer},
    )
    def patch(self, request, run_id: int):
        serializer = WorkspaceFileSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = _get_tier_workspace_run(run_id, get_or_create_player(request.user))
        run = ADVENTURE_TIER_WORKSPACE_FILES.write_file(
            run=run,
            path=serializer.validated_data["path"],
            content=serializer.validated_data.get("content", ""),
        )
        run = AdventureLevelTierRunService.hydrate_run(run)
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run))

    @extend_schema(
        request=WorkspaceFileRenameSerializer,
        responses={200: AdventureLevelTierRunResponseSerializer},
    )
    def put(self, request, run_id: int):
        serializer = WorkspaceFileRenameSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        run = _get_tier_workspace_run(run_id, get_or_create_player(request.user))
        run = ADVENTURE_TIER_WORKSPACE_FILES.rename_file(
            run=run,
            path=serializer.validated_data["path"],
            new_path=serializer.validated_data["new_path"],
        )
        run = AdventureLevelTierRunService.hydrate_run(run)
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run))

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="path",
                type={"type": "string", "maxLength": 240},
                location=OpenApiParameter.QUERY,
                required=True,
            )
        ],
        responses={200: AdventureLevelTierRunResponseSerializer},
    )
    def delete(self, request, run_id: int):
        serializer = WorkspaceFilePathSerializer(data=request.data or request.query_params)
        serializer.is_valid(raise_exception=True)
        run = _get_tier_workspace_run(run_id, get_or_create_player(request.user))
        run = ADVENTURE_TIER_WORKSPACE_FILES.delete_file(
            run=run,
            path=serializer.validated_data["path"],
        )
        run = AdventureLevelTierRunService.hydrate_run(run)
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run))


class AdventureLevelTierRetryAPIView(APIView):
    @extend_schema(request=None, responses={201: AdventureLevelTierRunResponseSerializer})
    def post(self, request, run_id: int):
        player = get_or_create_player(request.user)
        prior = AdventureLevelTierRun.objects.select_related(
            "tier__adventure_level__chapter__story",
            "tier__adventure_level__chapter",
            "selected_variant",
        ).get(id=run_id, player=player)
        if prior.is_replay:
            raise Locked("Replay runs cannot be retried.")
        run = AdventureLevelTierRunService().start_run(
            player=player,
            tier=prior.tier,
            source_entry_point="retry",
            prior_run=prior,
        )
        prefetch_run_payload_context(run)
        return Response(tier_run_payload(run), status=201)


def _get_tier_workspace_run(run_id: int, player) -> AdventureLevelTierRun:
    return AdventureLevelTierRun.objects.select_related(
        "tier__adventure_level__chapter__story",
        "tier__adventure_level__chapter",
        "current_wave",
        "selected_variant",
    ).get(id=run_id, player=player)
