import pytest
from django.test import override_settings

from ai_support.provider import AIProviderUnavailable
from ai_support.services import SYSTEM_PROMPT, AIChatService


class RecordingProvider:
    def __init__(self, reply="A branch is a movable reference."):
        self.reply_text = reply
        self.messages = None

    def complete(self, messages):
        self.messages = messages
        return self.reply_text


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_service_builds_minimal_conceptual_prompt_without_private_state():
    provider = RecordingProvider()
    service = AIChatService(provider=provider)

    result = service.reply(
        message="What is a branch?",
        history=[
            {"role": "user", "content": "What is HEAD?"},
            {"role": "assistant", "content": "HEAD is your current position."},
        ],
        page_context="stories",
    )

    assert result.policy_status == "allowed"
    assert provider.messages[0]["content"] == SYSTEM_PROMPT
    assert provider.messages[1]["content"].endswith("stories.")
    prompt_text = " ".join(item["content"] for item in provider.messages)
    assert "repository_state" not in prompt_text
    assert "solution_commands" not in prompt_text


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_service_does_not_call_provider_for_redirected_request():
    provider = RecordingProvider()

    result = AIChatService(provider=provider).reply(
        message="Give me the exact command for this challenge",
        history=[],
        page_context="home",
    )

    assert result.policy_status == "redirected"
    assert provider.messages is None


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_service_sends_off_topic_request_to_provider_for_contextual_redirect():
    provider = RecordingProvider(
        "That is outside my lane, but we can return to how Git branches work."
    )

    result = AIChatService(provider=provider).reply(
        message="Write a JavaScript calculator for me.",
        history=[],
        page_context="home",
    )

    assert result.policy_status == "allowed"
    assert "outside my lane" in result.reply
    assert provider.messages is not None
    assert provider.messages[-1]["content"] == "Write a JavaScript calculator for me."


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_service_sends_contextual_confusion_follow_up_to_provider():
    provider = RecordingProvider("Think of a branch as a movable bookmark.")

    result = AIChatService(provider=provider).reply(
        message="I don't understand.",
        history=[
            {"role": "user", "content": "What is a Git branch?"},
            {"role": "assistant", "content": "A branch is a movable reference."},
        ],
        page_context="stories",
    )

    assert result.policy_status == "allowed"
    assert provider.messages is not None
    assert provider.messages[-1]["content"] == "I don't understand."


@override_settings(AI_CHAT_ENABLED=False, GROQ_API_KEY="")
def test_service_reports_unavailable_when_disabled():
    with pytest.raises(AIProviderUnavailable):
        AIChatService(provider=RecordingProvider()).reply(
            message="What is a branch?",
            history=[],
            page_context="home",
        )


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="")
def test_service_reports_unavailable_when_key_is_missing():
    with pytest.raises(AIProviderUnavailable):
        AIChatService(provider=RecordingProvider()).reply(
            message="What is a branch?",
            history=[],
            page_context="home",
        )


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_service_marks_post_filtered_provider_response_as_redirected():
    result = AIChatService(
        provider=RecordingProvider("The exact command is git reset --hard")
    ).reply(
        message="How does reset work?",
        history=[],
        page_context="home",
    )

    assert result.policy_status == "redirected"
    assert "git reset" not in result.reply
