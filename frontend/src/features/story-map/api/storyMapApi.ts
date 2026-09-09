import { apiOperationRequest } from '@/shared/api/httpClient'
import type { ChapterContentOverview } from '@/features/story-map/types'
import type { ChapterBook } from '@/features/story-map/components/book/bookTypes'
import type {
  ChapterOrientationLessonDetail,
  ChapterOrientationLessonSummary,
} from '@/features/story-map/orientation/types'

export const storyMapApi = {
  listStories() {
    return apiOperationRequest('stories_list', '/stories/')
  },
  listChapters(storySlug?: string | null) {
    const query = storySlug ? `?story=${encodeURIComponent(storySlug)}` : ''
    return apiOperationRequest('chapters_list', `/chapters/${query}`)
  },
  getChapterOverview(chapterId: number) {
    return apiOperationRequest<'chapters_overview_retrieve', ChapterContentOverview>(
      'chapters_overview_retrieve',
      `/chapters/${chapterId}/overview/`,
    )
  },
  getChapterBook(chapterId: number) {
    return apiOperationRequest<'chapters_book_retrieve', ChapterBook>(
      'chapters_book_retrieve',
      `/chapters/${chapterId}/book/`,
    )
  },
  listOrientationLessons(chapterId: number) {
    return apiOperationRequest<'chapters_orientation_list', ChapterOrientationLessonSummary[]>(
      'chapters_orientation_list',
      `/chapters/${chapterId}/orientation/`,
    )
  },
  getOrientationLesson(lessonId: number) {
    return apiOperationRequest<'orientation_lessons_retrieve', ChapterOrientationLessonDetail>(
      'orientation_lessons_retrieve',
      `/orientation-lessons/${lessonId}/`,
    )
  },
  completeOrientationLesson(lessonId: number, highestStepSeen: number) {
    return apiOperationRequest<'orientation_lessons_complete_create', ChapterOrientationLessonDetail>(
      'orientation_lessons_complete_create',
      `/orientation-lessons/${lessonId}/complete/`,
      { body: { highest_step_seen: highestStepSeen } },
    )
  },
}
