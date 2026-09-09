from django.urls import path

from curriculum.views import (
    ChapterBookAPIView,
    ChapterContentOverviewAPIView,
    ChapterListAPIView,
    ChapterOrientationLessonListAPIView,
    CommandFormPreviewAPIView,
    LearnedSkillsAPIView,
    OrientationLessonCompleteAPIView,
    OrientationLessonDetailAPIView,
    StoryListAPIView,
)

urlpatterns = [
    path("stories/", StoryListAPIView.as_view(), name="stories"),
    path("chapters/", ChapterListAPIView.as_view(), name="chapters"),
    path(
        "chapters/<int:chapter_id>/overview/",
        ChapterContentOverviewAPIView.as_view(),
        name="chapter-overview",
    ),
    path("chapters/<int:chapter_id>/book/", ChapterBookAPIView.as_view(), name="chapter-book"),
    path(
        "chapters/<int:chapter_id>/orientation/",
        ChapterOrientationLessonListAPIView.as_view(),
        name="chapter-orientation-lessons",
    ),
    path(
        "orientation-lessons/<int:lesson_id>/",
        OrientationLessonDetailAPIView.as_view(),
        name="orientation-lesson-detail",
    ),
    path(
        "orientation-lessons/<int:lesson_id>/complete/",
        OrientationLessonCompleteAPIView.as_view(),
        name="orientation-lesson-complete",
    ),
    path("skills/learned/", LearnedSkillsAPIView.as_view(), name="skills-learned"),
    path(
        "command-forms/<int:form_id>/preview/",
        CommandFormPreviewAPIView.as_view(),
        name="command-form-preview",
    ),
]
