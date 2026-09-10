import pytest

from ai_support.serializers import AIChatRequestSerializer


def valid_payload(**overrides):
    payload = {
        "message": "What is HEAD?",
        "history": [],
        "page_context": "home",
    }
    payload.update(overrides)
    return payload


def test_request_serializer_trims_message_and_accepts_complete_history():
    serializer = AIChatRequestSerializer(
        data=valid_payload(
            message="  What is HEAD?  ",
            history=[
                {"role": "user", "content": "What is a commit?"},
                {"role": "assistant", "content": "A commit is a snapshot."},
            ],
        )
    )

    assert serializer.is_valid(), serializer.errors
    assert serializer.validated_data["message"] == "What is HEAD?"


@pytest.mark.parametrize(
    ("overrides", "field"),
    [
        ({"message": ""}, "message"),
        ({"message": "x" * 1001}, "message"),
        ({"page_context": "challenge_run"}, "page_context"),
        ({"surprise": True}, "surprise"),
        (
            {
                "history": [
                    {"role": "user", "content": "one"},
                    {"role": "user", "content": "two"},
                ]
            },
            "history",
        ),
        ({"history": [{"role": "assistant", "content": "orphan"}]}, "history"),
    ],
)
def test_request_serializer_rejects_invalid_payloads(overrides, field):
    serializer = AIChatRequestSerializer(data=valid_payload(**overrides))

    assert serializer.is_valid() is False
    assert field in serializer.errors


def test_history_message_rejects_unknown_fields():
    serializer = AIChatRequestSerializer(
        data=valid_payload(
            history=[
                {"role": "user", "content": "Question", "secret": "no"},
                {"role": "assistant", "content": "Answer"},
            ]
        )
    )

    assert serializer.is_valid() is False
    assert "history" in serializer.errors
