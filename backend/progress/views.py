from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView

from common.openapi import WalletSummaryResponseSerializer
from players.services import get_or_create_player
from progress.serializers import (
    DashboardSummaryResponseSerializer,
    PerformanceSummaryResponseSerializer,
    StatsSummaryResponseSerializer,
)
from progress.services import MetricsService
from progress.wallet import WalletService


class DashboardSummaryAPIView(APIView):
    @extend_schema(responses={200: DashboardSummaryResponseSerializer})
    def get(self, request):
        player = get_or_create_player(request.user)
        return Response(MetricsService().dashboard_summary(player=player))


class StatsSummaryAPIView(APIView):
    @extend_schema(responses={200: StatsSummaryResponseSerializer})
    def get(self, request):
        player = get_or_create_player(request.user)
        return Response(MetricsService().stats_summary(player=player))


class PerformanceSummaryAPIView(APIView):
    @extend_schema(responses={200: PerformanceSummaryResponseSerializer})
    def get(self, request):
        player = get_or_create_player(request.user)
        return Response(MetricsService().performance_summary(player=player))


class WalletSummaryAPIView(APIView):
    @extend_schema(responses={200: WalletSummaryResponseSerializer})
    def get(self, request):
        player = get_or_create_player(request.user)
        return Response(WalletService().summary(player=player))
