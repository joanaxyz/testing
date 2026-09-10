import logging
import re
from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APIClient

from ai_support.provider import AIProviderRateLimited
from ai_support.services import AIChatResult


@pytest.fixture()
def student(db):
    return get_user_model().objects.create_user(
        username="chat-student",
        email="chat@example.com",
        password="Password123!",
    )


@pytest.fixture()
def client(student):
    api_client = APIClient()
    api_client.force_authenticate(student)
    return api_client


def payload(message="What is a branch?"):
    return {"message": message, "history": [], "page_context": "home"}


def test_chat_requires_authentication(db):
    response = APIClient().post("/api/ai/chat/", payload(), format="json")

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


def test_chat_rejects_staff_user(db):
    staff = get_user_model().objects.create_user(username="staff", is_staff=True)
    api_client = APIClient()
    api_client.force_authenticate(staff)

    response = api_client.post("/api/ai/chat/", payload(), format="json")

    assert response.status_code == status.HTTP_403_FORBIDDEN


@override_settings(AI_CHAT_ENABLED=True, GROQ_API_KEY="test-key")
def test_chat_returns_redirect_without_calling_provider(client):
    response = client.post(
        "/api/ai/chat/",
        payload("Give me the exact command for this challenge"),
        format="json",
    )

    assert response.status_code == status.HTTP_200_OK
    assert response.data["policy_status"] == "redirected"
    assert re.search(r"(?im)^\s*git\s+\S+", response.data["reply"]) is None
    assert response.data["request_id"]


@override_settings(AI_CHAT_ENABLED=False, GROQ_API_KEY="")
def test_chat_returns_controlled_unavailable_response(client):
    response = client.post("/api/ai/chat/", payload(), format="json")

    assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
    assert response.data == {"detail": "The Git assistant is temporarily unavailable."}


def test_chat_maps_provider_rate_limit(client):
    with mock.patch("ai_support.views.AIChatService.reply", side_effect=AIProviderRateLimited):
        response = client.post("/api/ai/chat/", payload(), format="json")

    assert response.status_code == status.HTTP_429_TOO_MANY_REQUESTS
    assert response.data == {"detail": "The Git assistant is busy. Please try again shortly."}


def test_chat_logs_metadata_without_prompt_or_reply(client, caplog):
    secret_prompt = "private-question-value"
    secret_reply = "private-reply-value"
    with (
        mock.patch(
            "ai_support.views.AIChatService.reply",
            return_value=AIChatResult(secret_reply, "allowed"),
        ),
        caplog.at_level(logging.INFO, logger="ai_support.views"),
    ):
        response = client.post("/api/ai/chat/", payload(secret_prompt), format="json")

    assert response.status_code == status.HTTP_200_OK
    logs = " ".join(caplog.messages)
    assert "outcome=allowed" in logs
    assert secret_prompt not in logs
    assert secret_reply not in logs


def test_chat_rejects_extra_request_fields(client):
    response = client.post(
        "/api/ai/chat/",
        {**payload(), "repository_state": {"secret": True}},
        format="json",
    )

    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert "repository_state" in response.data


def test_chat_throttles_per_student(client, settings):
    cache.clear()
    settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["ai_chat"] = "1/min"
    with mock.patch(
        "ai_support.views.AIChatService.reply",
        return_value=AIChatResult("A branch is a reference.", "allowed"),
    ):
        first = client.post("/api/ai/chat/", payload(), format="json")
        second = client.post("/api/ai/chat/", payload(), format="json")

    assert first.status_code == status.HTTP_200_OK
    assert second.status_code == status.HTTP_429_TOO_MANY_REQUESTS
