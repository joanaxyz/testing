from rest_framework import serializers


class RateMetricSerializer(serializers.Serializer):
    value = serializers.FloatField(allow_null=True)
    numerator = serializers.IntegerField()
    denominator = serializers.IntegerField()


class DashboardKpiSetSerializer(serializers.Serializer):
    scr = RateMetricSerializer()
    arc = RateMetricSerializer()
    hlcr = RateMetricSerializer()


class PerformanceKpiSetSerializer(serializers.Serializer):
    scr = RateMetricSerializer()
    car = RateMetricSerializer()
    hlcr = RateMetricSerializer()
    rtr = RateMetricSerializer()
    arc = RateMetricSerializer()


class PerformanceModuleSerializer(serializers.Serializer):
    number = serializers.IntegerField()
    title = serializers.CharField()
    scr = RateMetricSerializer()
    hlcr = RateMetricSerializer()
    rtr = RateMetricSerializer()
    arc = RateMetricSerializer()


class PerformanceSummaryResponseSerializer(serializers.Serializer):
    kpis = PerformanceKpiSetSerializer()
    completed_sessions = serializers.IntegerField()
    modules = PerformanceModuleSerializer(many=True)


class DashboardCountsSerializer(serializers.Serializer):
    started = serializers.IntegerField()
    completed = serializers.IntegerField()
    failed = serializers.IntegerField()
    abandoned = serializers.IntegerField()


class DashboardStreakSerializer(serializers.Serializer):
    current = serializers.IntegerField()
    longest = serializers.IntegerField()
    last_completed_on = serializers.DateField(allow_null=True)


class DashboardRetryTrendSerializer(serializers.Serializer):
    level_title = serializers.CharField()
    attempts = serializers.IntegerField()
    retries = serializers.IntegerField()
    label = serializers.CharField()


class StatsSkillAxisSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    hint = serializers.CharField()
    value = serializers.FloatField(allow_null=True)
    command = serializers.CharField()


class StatsTrendPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    levels_completed = serializers.IntegerField()
    commands_run = serializers.IntegerField()


class StatsScopedCountSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    scope = serializers.CharField()


class StatsHeadlineSerializer(serializers.Serializer):
    levels_completed = serializers.IntegerField()
    finish_rate = RateMetricSerializer()
    accuracy = serializers.FloatField(allow_null=True)
    boss_floors = StatsScopedCountSerializer()
    comebacks = StatsScopedCountSerializer()
    perfect_clears = serializers.IntegerField()
    day_streak = serializers.IntegerField()
    longest_streak = serializers.IntegerField()
    gitcoins = serializers.IntegerField()
    commands_run = serializers.IntegerField()


class StatsSummaryResponseSerializer(serializers.Serializer):
    skill_profile = StatsSkillAxisSerializer(many=True)
    activity_trend = StatsTrendPointSerializer(many=True)
    headline = StatsHeadlineSerializer()


class DashboardSummaryResponseSerializer(serializers.Serializer):
    kpis = DashboardKpiSetSerializer()
    chapter_kpis = serializers.DictField(child=DashboardKpiSetSerializer())
    counts = DashboardCountsSerializer()
    completed_story_slug = serializers.CharField(allow_null=True)
    completed_stories = serializers.ListField(child=serializers.CharField())
    streak = DashboardStreakSerializer()
    perfect_clears = serializers.IntegerField()
    mastery = serializers.FloatField()
    retry_trends = DashboardRetryTrendSerializer(many=True)
