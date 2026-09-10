from django.urls import path

from ai_support.views import AIChatbotAPIView

urlpatterns = [
    path("chat/", AIChatbotAPIView.as_view(), name="ai-chat"),
]
