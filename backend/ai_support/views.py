import logging
import time
import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from ai_support.provider import AIProviderRateLimited, AIProviderUnavailable
from ai_support.serializers import (
    AIChatErrorSerializer,
    AIChatRequestSerializer,
    AIChatResponseSerializer,
)
from ai_support.services import AIChatService
from common.permissions import IsStudent

logger = logging.getLogger(__name__)


class AIChatbotAPIView(APIView):
    permission_classes = [IsStudent]
    throttle_scope = "ai_chat"

    @extend_schema(
        operation_id="ai_chat_create",
        request=AIChatRequestSerializer,
        responses={
            200: AIChatResponseSerializer,
            429: AIChatErrorSerializer,
            503: AIChatErrorSerializer,
        },
        tags=["ai-support"],
    )
    def post(self, request):
        request_id = uuid.uuid4()
        started = time.monotonic()
        serializer = AIChatRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        outcome = "provider_error"
        response_status = status.HTTP_503_SERVICE_UNAVAILABLE
        try:
            result = AIChatService().reply(**serializer.validated_data)
            outcome = result.policy_status
            response_status = status.HTTP_200_OK
            response = AIChatResponseSerializer(
                {
                    "reply": result.reply,
                    "policy_status": result.policy_status,
                    "request_id": request_id,
                }
            )
            return Response(response.data)
        except AIProviderRateLimited:
            outcome = "rate_limited"
            response_status = status.HTTP_429_TOO_MANY_REQUESTS
            return Response(
                {"detail": "The Git assistant is busy. Please try again shortly."},
                status=response_status,
            )
        except AIProviderUnavailable:
            return Response(
                {"detail": "The Git assistant is temporarily unavailable."},
                status=response_status,
            )
        finally:
            latency_ms = round((time.monotonic() - started) * 1000)
            logger.info(
                "ai_chat_completed request_id=%s outcome=%s status=%s latency_ms=%s",
                request_id,
                outcome,
                response_status,
                latency_ms,
            )
