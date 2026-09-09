import { BookOpenText, Check, ClipboardList, Star } from 'lucide-react'
import type { ComponentType, ReactNode } from 'react'

import { TaskSealIcon } from '@/shared/level/components/workspaceIcons'

import { GitCoinIcon } from '@/shared/wallet/components/GitCoinIcon'
import type { NormalizedLevelContext, ObjectiveCheck } from '@/shared/level/utils/levelContext'
import { Badge, type BadgeProps } from '@/shared/components/Badge'
import { Card, CardContent, CardHeader, CardTitle } from '@/shared/components/Card'
import { CopyButton } from '@/shared/components/CopyButton'
import { cn } from '@/shared/utils/cn'

export type LevelContextTag = {
  label: string
  variant?: BadgeProps['variant']
}

export type LevelFact = {
  label: string
  icon: ComponentType<{ className?: string }>
  /** Optional icon tint override (the mock renders the star/reward glyphs amber). */
  iconClass?: string
  value: ReactNode
}

export type LevelStoryCardLabels = {
  story: string
  task: string
  details: string
  detailsAriaLabel: string
}

const defaultLabels: LevelStoryCardLabels = {
  story: 'Story',
  task: 'Task',
  details: 'Copy details',
  detailsAriaLabel: 'Values referenced by the story and task',
}

export function StarTriplet({ count, className }: { count: number; className?: string }) {
  return (
    <span className={cn('gameplay-header-stars', className)} aria-label={`${count} of 3 stars`}>
      {Array.from({ length: 3 }).map((_, index) => (
        <Star key={index} aria-hidden="true" className={index < count ? 'is-lit' : ''} />
      ))}
    </span>
  )
}

export function DifficultyChip({ difficulty }: { difficulty: string }) {
  return (
    <span className={cn('lvlctx-chip', `lvlctx-chip--${difficulty.toLowerCase()}`)}>
      {difficulty.charAt(0).toUpperCase() + difficulty.slice(1)}
    </span>
  )
}

export function RewardValue({ coins }: { coins: number }) {
  return (
    <span className="lvlctx-reward">
      <GitCoinIcon />
      <span>{coins.toLocaleString()} GitCoins</span>
    </span>
  )
}

/**
 * The reference mock's LEVEL CONTEXT panel, shared by both workspaces: panel
 * eyebrow over a hairline, icon-led title, STORY / TASK sections, then the
 * icon fact rows. No nested boxes.
 *
 * The live objective checklist is an adventure-only scaffold: the adventure
 * caller passes the evaluated rows via `checks`; challenges rely on the
 * expected-state reveal instead.
 */
export function LevelStoryCard({
  title,
  titleIcon: TitleIcon,
  context,
  facts,
  className,
  checks,
  labels,
  showHeader = true,
  showDetailLabels = false,
  tourTarget,
  tags,
}: {
  title: string
  titleIcon?: ComponentType<{ className?: string }>
  context: NormalizedLevelContext
  facts?: LevelFact[]
  className?: string
  checks?: ObjectiveCheck[]
  labels?: Partial<LevelStoryCardLabels>
  /** The workspace command bar can own the level title on denser layouts. */
  showHeader?: boolean
  /** Challenge tasks benefit from naming each literal beside its copy action. */
  showDetailLabels?: boolean
  /** Optional stable anchor for contextual onboarding without coupling to layout wrappers. */
  tourTarget?: string
  /** Optional pill row above the story/task sections (e.g. "Module 1", "Medium",
   * "Changed variant"). Opt-in - omitted entirely when not passed. */
  tags?: LevelContextTag[]
}) {
  const sectionLabels = { ...defaultLabels, ...labels }

  return (
    <Card
      aria-label={showHeader ? undefined : title}
      className={cn('lvlctx shadow-none', className)}
      data-tour-target={tourTarget}
    >
      {showHeader ? (
        <CardHeader className="lvlctx-header">
          <span className="panel-eyebrow">Level Context</span>
          <div className="lvlctx-titlerow">
            {TitleIcon ? <TitleIcon aria-hidden="true" /> : null}
            <CardTitle className="lvlctx-title">{title}</CardTitle>
          </div>
        </CardHeader>
      ) : null}
      <CardContent className="lvlctx-body app-scrollbar">
        {tags?.length ? (
          <div className="lvlctx-tags" aria-label="Scenario tags">
            {tags.map((tag) => (
              <Badge key={tag.label} variant={tag.variant}>
                {tag.label}
              </Badge>
            ))}
          </div>
        ) : null}

        <Section icon={BookOpenText} title={sectionLabels.story} hidden={!context.story}>
          <p className="lvlctx-story">{context.story}</p>
        </Section>

        <Section icon={TaskSealIcon} title={sectionLabels.task} hidden={!context.task}>
          <p className="lvlctx-task">{context.task}</p>
        </Section>

        <Section icon={TaskSealIcon} title="Objective" hidden={!checks?.length}>
          <ul className="lvlctx-checks">
            {(checks ?? []).map((check) => (
              <li className={cn('lvlctx-check', check.satisfied && 'is-done')} key={check.label}>
                <span className="lvlctx-check-dot" aria-hidden="true">
                  {check.satisfied ? <Check /> : null}
                </span>
                <span className="lvlctx-check-label">{check.label}</span>
              </li>
            ))}
          </ul>
        </Section>

        {/* Required names (folder, branch, ...) sit right under the objective:
            the story references them and the panel bottom is the first thing
            to scroll out of view on short viewports. */}
        <Section
          icon={ClipboardList}
          title={sectionLabels.details}
          hidden={!context.details.length}
        >
          <ul className="lvlctx-copies" aria-label={sectionLabels.detailsAriaLabel}>
            {context.details.map((item) => (
              <li className="lvlctx-copy" key={`${item.label}:${item.value}`}>
                {item.label ? (
                  <span className={cn('lvlctx-copy-label', !showDetailLabels && 'sr-only')}>
                    {item.label}
                  </span>
                ) : null}
                <code>{item.value}</code>
                <CopyButton
                  value={item.value}
                  label={item.label || item.value}
                  className="lvlctx-copy-btn"
                />
              </li>
            ))}
          </ul>
        </Section>

        {facts?.length ? (
          <section className="lvlctx-section">
            <dl className="lvlctx-facts">
              {facts.map((fact) => (
                <div className="lvlctx-fact" key={fact.label}>
                  <dt>
                    <fact.icon aria-hidden="true" className={fact.iconClass} />
                    {fact.label}
                  </dt>
                  <dd>{fact.value}</dd>
                </div>
              ))}
            </dl>
          </section>
        ) : null}
      </CardContent>
    </Card>
  )
}

function Section({
  children,
  hidden,
  icon: Icon,
  title,
}: {
  children: ReactNode
  hidden?: boolean
  icon: ComponentType<{ className?: string }>
  title: string
}) {
  if (hidden) return null
  return (
    <section className="lvlctx-section">
      <div className="lvlctx-eyebrow">
        <Icon aria-hidden="true" />
        {title}
      </div>
      {children}
    </section>
  )
}
