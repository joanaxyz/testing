// Ported from archive/may30-old-modules:
// frontend/src/features/modules/orientation/OrientationLessonWorkspace.tsx
// Rewired to this branch's API/types: modulesApi -> storyMapApi, LessonDetail
// -> ChapterOrientationLessonDetail, LearningModule -> LearningChapter.
// Session plumbing (needsSession/sessionQuery/resetOrientationSession) is
// dropped entirely - no lesson here needs a live simulated terminal anymore
// (git_command/shell_command steps render as static cards, see
// OrientationStepView).

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle2 } from 'lucide-react'
import { useEffect, useMemo, useState } from 'react'

import { storyMapApi } from '@/features/story-map/api/storyMapApi'
import { OrientationStepView } from '@/features/story-map/orientation/OrientationStepView'
import {
  CRITICAL_LESSON_SLUGS,
  displayLessonTitle,
  LESSON_LAYOUT_BY_SLUG,
  type OrientationLayout,
} from '@/features/story-map/orientation/types'
import type { LearningChapter } from '@/features/story-map/types'
import { queryKeys } from '@/shared/api/queryKeys'
import { Badge } from '@/shared/components/Badge'
import { Button } from '@/shared/components/Button'
import { GamePanel } from '@/shared/components/GamePanel'
import { LoadingState } from '@/shared/components/LoadingState'
import { ErrorState } from '@/shared/components/ErrorState'
import { cn } from '@/shared/utils/cn'

export function OrientationLessonWorkspace({ chapter }: { chapter: LearningChapter }) {
  const queryClient = useQueryClient()

  const lessonsQuery = useQuery({
    queryKey: queryKeys.orientationLessons(chapter.id),
    queryFn: () => storyMapApi.listOrientationLessons(chapter.id),
    staleTime: 60 * 1000,
  })
  const lessons = useMemo(
    () => [...(lessonsQuery.data ?? [])].sort((a, b) => a.sort_order - b.sort_order),
    [lessonsQuery.data],
  )
  const [activeLessonId, setActiveLessonId] = useState<number | null>(null)

  useEffect(() => {
    setActiveLessonId((current) => {
      if (current && lessons.some((lesson) => lesson.id === current)) return current
      return lessons[0]?.id ?? null
    })
  }, [lessons])

  const lessonDetailQuery = useQuery({
    queryKey: queryKeys.orientationLesson(activeLessonId ?? 0),
    queryFn: () => storyMapApi.getOrientationLesson(activeLessonId!),
    enabled: Boolean(activeLessonId),
    staleTime: 60 * 1000,
  })
  const lesson = lessonDetailQuery.data

  const steps = lesson?.interaction_steps ?? []
  const layout: OrientationLayout = (lesson && LESSON_LAYOUT_BY_SLUG[lesson.slug]) ?? 'storyboard'

  const [stepIndex, setStepIndex] = useState(0)
  const [completedSteps, setCompletedSteps] = useState<Set<string>>(() => new Set())

  useEffect(() => {
    setStepIndex(0)
    setCompletedSteps(new Set())
  }, [activeLessonId])

  const completeMutation = useMutation({
    mutationFn: () => storyMapApi.completeOrientationLesson(lesson!.id, Math.max(steps.length - 1, 0)),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: queryKeys.orientationLesson(lesson!.id) })
      await queryClient.invalidateQueries({ queryKey: queryKeys.orientationLessons(chapter.id) })
    },
  })

  const currentStep = steps[stepIndex]
  const allStepsDone = steps.length > 0 && completedSteps.size >= steps.length
  const nextLessonId = useMemo(() => {
    if (!lesson) return null
    const currentIndex = lessons.findIndex((item) => item.id === lesson.id)
    if (currentIndex < 0 || currentIndex >= lessons.length - 1) return null
    return lessons[currentIndex + 1]?.id ?? null
  }, [lesson, lessons])

  const handleStepComplete = () => {
    if (!currentStep) return
    setCompletedSteps((previous) => new Set([...previous, currentStep.id]))
  }

  if (lessonsQuery.isLoading) {
    return <LoadingState label="Loading orientation" description="Preparing lessons for this chapter." variant="page" />
  }
  if (lessonsQuery.isError) {
    return <ErrorState title="Could not load orientation lessons" description={lessonsQuery.error.message} />
  }
  if (!lessons.length) {
    return <ErrorState title="No orientation lessons" description="This chapter has no published lessons yet." />
  }

  return (
    <div className="mx-auto flex max-w-5xl flex-col gap-5">
      <GamePanel as="section">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-2xl font-extrabold tracking-tight">{chapter.title}</h1>
          <div className="flex flex-wrap items-center gap-2">
            {lesson && CRITICAL_LESSON_SLUGS.has(lesson.slug) ? (
              <Badge variant="outline">Foundation critical</Badge>
            ) : null}
          </div>
        </div>

        <div className="mt-4 flex flex-wrap gap-2">
          {lessons.map((item) => (
            <button
              key={item.id}
              type="button"
              className={cn(
                'rounded-full px-3 py-1 text-xs font-medium transition',
                item.id === activeLessonId ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground',
                item.is_complete && 'ring-1 ring-primary/50',
              )}
              onClick={() => setActiveLessonId(item.id)}
            >
              {item.is_complete ? '✓ ' : ''}
              {displayLessonTitle(item.title)}
            </button>
          ))}
        </div>

        {!lesson || lessonDetailQuery.isLoading ? (
          <LoadingState label="Loading lesson" variant="inline" />
        ) : (
          <>
            <header className="mt-5 grid gap-2">
              <h2 className="text-3xl font-extrabold tracking-tight">{displayLessonTitle(lesson.title)}</h2>
              <p className="text-muted-foreground">{lesson.subtitle}</p>
              {lesson.content_html ? (
                <div
                  className="prose prose-invert max-w-none text-sm text-muted-foreground"
                  dangerouslySetInnerHTML={{ __html: lesson.content_html }}
                />
              ) : null}
            </header>

            <div className="mt-4 flex flex-wrap gap-2">
              {steps.map((step, index) => (
                <button
                  key={step.id}
                  type="button"
                  className={cn(
                    'rounded-full px-3 py-1 text-xs font-medium transition',
                    index === stepIndex ? 'bg-primary text-primary-foreground' : 'bg-secondary text-muted-foreground',
                    completedSteps.has(step.id) && 'ring-1 ring-primary/50',
                  )}
                  onClick={() => setStepIndex(index)}
                >
                  {completedSteps.has(step.id) ? '✓ ' : ''}
                  {step.title}
                </button>
              ))}
            </div>

            <div className="mt-5">
              {layout === 'guide_terminal' ? (
                <div className="mb-5 rounded-lg border border-border bg-secondary/20 p-4">
                  <h2 className="text-sm font-bold uppercase tracking-wide text-muted-foreground">Guide</h2>
                  <p className="mt-2 text-sm leading-7 text-muted-foreground">
                    Install Git on your machine, then review the configuration commands below. Values you set become
                    authorship metadata on every commit.
                  </p>
                </div>
              ) : null}
              {currentStep ? (
                <OrientationStepView
                  key={currentStep.id}
                  step={currentStep}
                  layout={layout}
                  onStepComplete={handleStepComplete}
                  hasNextStep={stepIndex < steps.length - 1}
                  onContinueToNext={() => setStepIndex((current) => Math.min(current + 1, steps.length - 1))}
                />
              ) : null}
            </div>
          </>
        )}
      </GamePanel>

      {lesson && !lessonDetailQuery.isLoading ? (
        <GamePanel as="section" className="flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-start gap-3">
            <CheckCircle2 className="mt-0.5 size-5 text-primary" />
            <div>
              <h2 className="text-lg font-bold">Mark as complete</h2>
              <p className="mt-1 text-sm leading-6 text-muted-foreground">
                Finish all steps above, then mark this lesson complete.
              </p>
            </div>
          </div>
          <Button
            type="button"
            disabled={lesson.is_complete || !allStepsDone || completeMutation.isPending}
            onClick={() => completeMutation.mutate()}
          >
            {lesson.is_complete
              ? 'Completed'
              : completeMutation.isPending
                ? 'Saving…'
                : allStepsDone
                  ? 'Mark as complete'
                  : `Complete steps (${completedSteps.size}/${steps.length})`}
          </Button>
          {lesson.is_complete && nextLessonId ? (
            <Button type="button" variant="outline" onClick={() => setActiveLessonId(nextLessonId)}>
              Next topic
            </Button>
          ) : null}
        </GamePanel>
      ) : null}
    </div>
  )
}
