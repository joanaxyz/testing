import { type CSSProperties, useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router-dom'
import { PanelLeftOpen, PanelRightOpen, X } from 'lucide-react'

import { StoryAdventurePath } from '@/features/story-map/components/path/StoryAdventurePath'
import { ChapterOverview } from '@/features/story-map/components/ChapterOverview'
import { OrientationLessonWorkspace } from '@/features/story-map/orientation/OrientationLessonWorkspace'
import { StoryChapterList } from '@/features/story-map/components/StoryChapterList'
import { StoryOnboarding } from '@/features/story-map/components/StoryOnboarding'
import { StoryCompanionPanel, StorySkillFocusPanel } from '@/features/story-map/components/StorySidePanels'
import { storyMapApi } from '@/features/story-map/api/storyMapApi'
import { useStories } from '@/features/story-map/hooks/useStories'
import { chapterTitle, firstOpenChapter } from '@/features/story-map/utils/storyMapChapter'
import { queryKeys } from '@/shared/api/queryKeys'
import { EmptyState } from '@/shared/components/EmptyState'
import { ErrorState } from '@/shared/components/ErrorState'
import { LoadingState } from '@/shared/components/LoadingState'
import { usePlayerLoadout } from '@/shared/player-loadout/usePlayerLoadout'
import { useAuthStore } from '@/shared/auth/useAuth'
import { STORIES_ROUTE } from '@/shared/navigation/routes'
import { getStoryWorld } from '@/shared/story-worlds/registry'
import { storyWorldStyle } from '@/shared/story-worlds/theme'

const COMPACT_STORY_MAP_QUERY = '(max-width: 1120px)'

function useCompactStoryMap() {
  const [compact, setCompact] = useState(
    () => typeof window !== 'undefined' && typeof window.matchMedia === 'function'
      ? window.matchMedia(COMPACT_STORY_MAP_QUERY).matches
      : false,
  )

  useEffect(() => {
    if (typeof window.matchMedia !== 'function') return
    const media = window.matchMedia(COMPACT_STORY_MAP_QUERY)
    const update = () => setCompact(media.matches)
    update()
    media.addEventListener('change', update)
    return () => media.removeEventListener('change', update)
  }, [])

  return compact
}

export function StoryMapPage() {
  const userId = useAuthStore((state) => state.user?.id)
  const { storySlug: routeStorySlug } = useParams<{ storySlug: string }>()
  const storySlug = routeStorySlug ?? 'git-it-legacy'
  const [searchParams] = useSearchParams()
  const chapterParam = searchParams.get('chapter')
  const focusedChapterId = chapterParam ? Number(chapterParam) : null

  const chaptersQuery = useQuery({
    queryKey: queryKeys.storyChapters(storySlug),
    queryFn: () => storyMapApi.listChapters(storySlug),
    staleTime: 5 * 60 * 1000,
  })
  const storiesQuery = useStories()

  const chapters = useMemo(() => chaptersQuery.data ?? [], [chaptersQuery.data])
  const activeStory = useMemo(
    () => storiesQuery.data?.find((story) => story.slug === storySlug) ?? null,
    [storySlug, storiesQuery.data],
  )
  const { companion, companionSlug, hasCompanion, isLoading: loadoutLoading, isError: loadoutError } = usePlayerLoadout()
  const storyWorld = useMemo(() => getStoryWorld(activeStory?.world_slug ?? storySlug), [activeStory?.world_slug, storySlug])
  const storyMapStyle = {
    ...storyWorldStyle(storyWorld),
    backgroundImage: `url("${storyWorld.map?.background.src ?? '/cosmetics/story-worlds/arcane-spire/backgrounds/level-map.png'}")`,
  } as CSSProperties
  const [activeChapterId, setActiveChapterId] = useState<number | null>(null)
  const [leftRailOpen, setLeftRailOpen] = useState(false)
  const [rightRailOpen, setRightRailOpen] = useState(false)
  const compactStoryMap = useCompactStoryMap()

  useEffect(() => {
    if (!chapters.length) return

    setActiveChapterId((current) => {
      if (focusedChapterId && chapters.some((chapter) => chapter.id === focusedChapterId)) {
        return focusedChapterId
      }
      if (current && chapters.some((chapter) => chapter.id === current)) return current
      return firstOpenChapter(chapters)?.id ?? null
    })
  }, [chapters, focusedChapterId])

  useEffect(() => {
    setLeftRailOpen(false)
    setRightRailOpen(false)
  }, [activeChapterId, storySlug])

  const activeChapter = useMemo(
    () => chapters.find((chapter) => chapter.id === activeChapterId) ?? firstOpenChapter(chapters),
    [activeChapterId, chapters],
  )

  const overviewQuery = useQuery({
    queryKey: queryKeys.chapterOverview(activeChapter?.id ?? 0),
    queryFn: () => storyMapApi.getChapterOverview(activeChapter!.id),
    // Orientation chapters carry no AdventureLevel/ChallengeLevel content, so
    // their overview would always resolve to empty arrays - skip the request
    // and route them to OrientationLessonWorkspace instead (see render below).
    enabled: Boolean(activeChapter) && !activeChapter?.is_orientation,
    staleTime: 2 * 60 * 1000,
  })

  if (chaptersQuery.isLoading) {
    return <LoadingState companionSlug={companionSlug} description="Preparing the story map." label="Loading map" variant="page" />
  }
  if (chaptersQuery.isError) {
    return <ErrorState title="Could not load map" description={chaptersQuery.error.message} />
  }
  if (!chapters.length || !activeChapter) {
    return <EmptyState title="No map available" description="Publish chapters to start learning." />
  }

  const overview = overviewQuery.data ?? null
  const adventures = overview?.adventures ?? []
  const challenges = overview?.challenges ?? []
  const levels = adventures
  const challengesLocked = activeChapter.locked
  const leftRailHidden = compactStoryMap && !leftRailOpen
  const rightRailHidden = compactStoryMap && !rightRailOpen

  return (
    <div className="story-page-shell" style={storyWorldStyle(storyWorld)}>
      <div className="story-map-backdrop" style={storyMapStyle} aria-hidden="true" />

      <div className="story-map-rail-controls" aria-label="Map panels">
        <button
          type="button"
          aria-expanded={leftRailOpen}
          aria-controls="story-map-tools"
          onClick={() => setLeftRailOpen((open) => !open)}
        >
          <PanelLeftOpen aria-hidden="true" />
          Chapter tools
        </button>
        <button
          type="button"
          aria-expanded={rightRailOpen}
          aria-controls="story-map-utilities"
          onClick={() => setRightRailOpen((open) => !open)}
        >
          <PanelRightOpen aria-hidden="true" />
          Story utilities
        </button>
      </div>

      {(leftRailOpen || rightRailOpen) ? (
        <button
          type="button"
          className="story-map-rail-backdrop"
          aria-label="Close map panels"
          onClick={() => { setLeftRailOpen(false); setRightRailOpen(false) }}
        />
      ) : null}

      <div className="story-map-layout">
        <aside
          id="story-map-tools"
          className={`story-map-left ${leftRailOpen ? 'is-open' : ''}`}
          aria-label="Chapter tools"
          aria-hidden={leftRailHidden || undefined}
          inert={leftRailHidden || undefined}
        >
          <button type="button" className="story-map-rail-close" aria-label="Close chapter tools" onClick={() => setLeftRailOpen(false)}>
            <X aria-hidden="true" />
          </button>
          <ChapterOverview chapter={{ ...activeChapter, title: chapterTitle(activeChapter) }} />
        </aside>

        <section className="story-map-stage" aria-label={`${activeStory?.title ?? 'Story'} chapter map`}>
          <div className="story-switcher story-switcher--map" data-onboarding="stories">
            <Link to={STORIES_ROUTE} className="story-link">
              All stories
            </Link>
            {activeStory ? <span>{activeStory.title}</span> : null}
            {userId != null ? (
              <StoryOnboarding
                key={userId}
                ready={Boolean(overview) && !overviewQuery.isError && !loadoutLoading && !loadoutError}
                compact={compactStoryMap}
                hasCompanion={hasCompanion}
              />
            ) : null}
          </div>

          <h1 className="story-map-title">{activeStory?.title ?? 'Story'}</h1>

          {activeChapter.is_orientation ? (
            <OrientationLessonWorkspace chapter={activeChapter} />
          ) : overviewQuery.isError ? (
            <ErrorState title="Could not load chapter levels" description={overviewQuery.error.message} />
          ) : (
            <StoryAdventurePath
              chapter={activeChapter}
              levels={levels}
              challenges={challenges}
              challengesLocked={challengesLocked}
              loading={overviewQuery.isLoading}
            />
          )}
        </section>

        <aside
          id="story-map-utilities"
          className={`story-map-right ${rightRailOpen ? 'is-open' : ''}`}
          aria-label="Story chapters and companion"
          aria-hidden={rightRailHidden || undefined}
          inert={rightRailHidden || undefined}
        >
          <button type="button" className="story-map-rail-close" aria-label="Close story utilities" onClick={() => setRightRailOpen(false)}>
            <X aria-hidden="true" />
          </button>
          <StoryChapterList
            chapters={chapters}
            activeChapterId={activeChapter.id}
            onSelectChapter={setActiveChapterId}
          />
          <StorySkillFocusPanel
            levels={levels}
            companionSlug={hasCompanion ? companionSlug : null}
            companionLabel={hasCompanion ? companion.label : null}
            loading={overviewQuery.isLoading}
          />
          <StoryCompanionPanel companion={hasCompanion ? companion : null} />
        </aside>
      </div>
    </div>
  )
}
