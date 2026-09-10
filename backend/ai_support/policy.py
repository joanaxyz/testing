from __future__ import annotations

import re
from dataclasses import dataclass

_SCENARIO_MARKERS = re.compile(
    r"\b(?:scenario|challenge|trial|mission|level|exercise|task|workspace|"
    r"current problem|current objective)\b",
    re.IGNORECASE,
)
_ANSWER_REQUESTS = re.compile(
    r"\b(?:exact answer|exact command|commands? to (?:type|run|use)|"
    r"what (?:do|should) i type|solve (?:it|this|the)|give me (?:the )?answer|"
    r"command sequence|step[- ]by[- ]step commands?)\b",
    re.IGNORECASE,
)
_PROMPT_INJECTION = re.compile(
    r"\b(?:ignore (?:all |the )?(?:previous|prior|system) instructions?|"
    r"reveal (?:the )?system prompt|developer message|bypass (?:the )?policy|"
    r"pretend (?:there (?:is|are)|you have) no (?:rules|policy))\b",
    re.IGNORECASE,
)
_ENCODED_BLOB = re.compile(r"(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{48,}={0,2}(?![A-Za-z0-9+/])")
_COMMAND_LINE = re.compile(r"(?im)^\s*(?:\$\s*)?git\s+\S+")
_UNSAFE_RESPONSE = re.compile(
    r"\b(?:the exact (?:answer|command)|type (?:this|these) commands?|"
    r"run (?:these|the following) commands?)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class PolicyDecision:
    redirected: bool
    reason: str | None = None


class NoAnswerPolicyGuard:
    def classify(self, message: str) -> PolicyDecision:
        if _PROMPT_INJECTION.search(message):
            return PolicyDecision(True, "prompt_injection")
        if _ENCODED_BLOB.search(message):
            return PolicyDecision(True, "encoded_instructions")
        if _ANSWER_REQUESTS.search(message) and _SCENARIO_MARKERS.search(message):
            return PolicyDecision(True, "scenario_answer_request")
        if re.search(r"\b(?:command sequence|step[- ]by[- ]step commands?)\b", message, re.I):
            return PolicyDecision(True, "command_sequence_request")
        return PolicyDecision(False)

    def redirected_reply(self, message: str) -> str:
        lowered = message.lower()
        if "conflict" in lowered or "merge" in lowered:
            concept = "Think about which file states Git is asking you to reconcile and what a resolved file must contain."
            question = "What does the repository status say is still unresolved?"
        elif "branch" in lowered or "checkout" in lowered or "switch" in lowered:
            concept = "Think about the branch you are currently on and the branch reference you need to create or move to."
            question = "Which branch should HEAD point to when you finish?"
        elif "stage" in lowered or "add" in lowered:
            concept = "Separate the working tree from the staging area and identify which changes should enter the next snapshot."
            question = "Which files belong in the staging area at the target state?"
        elif "commit" in lowered:
            concept = "A commit records the staged snapshot, so first compare the working tree, staging area, and existing history."
            question = "What must be staged before the new snapshot can be recorded?"
        elif any(word in lowered for word in ("reset", "restore", "revert", "recover")):
            concept = "Recovery choices differ in whether they move a reference, change files, or add a new inverse snapshot."
            question = (
                "Which parts of repository state should change, and which history must remain?"
            )
        elif any(word in lowered for word in ("remote", "push", "pull", "fetch")):
            concept = "Distinguish downloading remote references, integrating them locally, and publishing local history."
            question = "Does the target state require transfer, integration, or both?"
        else:
            concept = "Start by comparing the current repository state with the requested target state one area at a time."
            question = (
                "What is the first state difference you can describe without naming a command?"
            )
        return (
            "I can’t provide the exact command or sequence for a GIT it! scenario. "
            f"{concept} {question}"
        )

    def filter_response(self, reply: str) -> str:
        command_lines = _COMMAND_LINE.findall(reply)
        if "```" in reply or len(command_lines) > 1 or _UNSAFE_RESPONSE.search(reply):
            return (
                "I can explain the Git concept, but I can’t provide an exact scenario answer or "
                "ordered command sequence. Focus on how the working tree, staging area, branches, "
                "and commit history differ from the target. Which state change are you trying to understand?"
            )
        return reply.strip()
