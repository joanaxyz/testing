from django.db import models


class VariantBase(models.Model):
    """Shared shape for authored problem variants (adventure waves, challenge
    trials): one authored case with an initial/target state pair, an
    evaluation spec, and scaffold policy. Concrete subclasses add only their
    parent FK."""

    # Variant slugs are rendered from authored case identifiers. Keep both
    # fields on the same explicit bound so bulk seeding cannot succeed on
    # SQLite and then fail against PostgreSQL's enforced varchar length.
    slug = models.SlugField(max_length=160)
    label = models.CharField(max_length=80)
    initial_state = models.JSONField(default=dict)
    evaluation_spec = models.JSONField(default=dict, blank=True)
    target_state = models.JSONField(default=dict, blank=True)
    solution_commands = models.JSONField(default=list, blank=True)
    # Mid-solution workspace file edits the player performs by hand during
    # live play (e.g. resolving a merge conflict in the editor) that the
    # offline target-state generator (frontend/scripts/generate-targets.mjs)
    # needs to replicate since it has no human to type the edit. Each entry:
    # {"mode": "write" | "create", "path": str, "content": str}. Optional
    # "after_command_index" (default 0) matches generate-targets.mjs's
    # convention for when mid-sequence the edit applies.
    solution_workspace_files = models.JSONField(default=list, blank=True)
    case_id = models.CharField(max_length=160, blank=True)
    semantic_key = models.CharField(max_length=240, blank=True)
    parameter_context = models.JSONField(default=dict, blank=True)
    scenario_context = models.JSONField(default=dict, blank=True)
    scaffold_policy = models.JSONField(default=dict, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta:
        abstract = True
