import { useQuery } from '@tanstack/react-query'
import {
  ChartNoAxesCombined,
  ChevronDown,
  CircleCheck,
  GitCompareArrows,
  RefreshCcw,
  ShieldCheck,
  Target,
  type LucideIcon,
} from 'lucide-react'
import type { CSSProperties } from 'react'

import { performanceApi } from '@/features/performance/api/performanceApi'
import type { PerformanceModule, RateMetric } from '@/features/performance/types'
import { ErrorState } from '@/shared/components/ErrorState'
import { LoadingState } from '@/shared/components/LoadingState'
import { queryKeys } from '@/shared/api/queryKeys'

type Tone = 'teal' | 'blue' | 'neutral' | 'green' | 'purple'

function metricValue(metric: RateMetric, average = false) {
  if (metric.value == null) return average ? '—' : '0%'
  return average ? metric.value.toFixed(2) : `${Math.round(metric.value)}%`
}

function MetricRing({ metric, tone, average = false }: { metric: RateMetric; tone: Tone; average?: boolean }) {
  const progress = metric.value == null ? 0 : average ? Math.min(metric.value / 3 * 100, 100) : metric.value
  return (
    <span
      className={`performance-ring is-${tone}`}
      style={{ '--metric-progress': `${progress * 3.6}deg` } as CSSProperties}
      aria-hidden="true"
    >
      <span />
    </span>
  )
}

function KpiCard({
  label,
  metric,
  subtext,
  tone,
  Icon,
  average = false,
}: {
  label: string
  metric: RateMetric
  subtext: string
  tone: Tone
  Icon: LucideIcon
  average?: boolean
}) {
  return (
    <article className={`performance-kpi is-${tone}`}>
      <div>
        <span className="performance-kpi-label"><Icon aria-hidden="true" />{label}</span>
        <strong>{metricValue(metric, average)}</strong>
        <small>{subtext}</small>
      </div>
      <MetricRing metric={metric} tone={tone} average={average} />
    </article>
  )
}

function ProgressRow({ label, metric, tone }: { label: string; metric: RateMetric; tone: Tone }) {
  const hasData = metric.denominator > 0
  const value = metric.value ?? 0
  return (
    <div className={`performance-row is-${tone}${hasData ? '' : ' is-empty'}`}>
      <div className="performance-row-head">
        <span>{label}</span>
        <strong>{hasData ? `${Math.round(value)}%` : '—'}</strong>
      </div>
      <div className="performance-bar"><span style={{ width: `${Math.max(0, Math.min(100, value))}%` }} /></div>
      <small>{hasData ? `${metric.numerator}/${metric.denominator} attempts` : 'Waiting for practice'}</small>
    </div>
  )
}

function ModuleCard({ module }: { module: PerformanceModule }) {
  return (
    <details className="performance-module" open>
      <summary>
        <span>Module {module.number}</span>
        {module.title.toLowerCase() !== `module ${module.number}` ? <strong>{module.title}</strong> : null}
        <ChevronDown aria-hidden="true" />
      </summary>
      <div className="performance-module-body">
        <ProgressRow label="Scenario Completion" metric={module.scr} tone="teal" />
        <div className="performance-module-split">
          <ProgressRow label="Hard Completion" metric={module.hlcr} tone="blue" />
          <ProgressRow label="Retry Transfer" metric={module.rtr} tone="green" />
        </div>
        <div className={`performance-retry-average${module.arc.denominator ? '' : ' is-empty'}`}>
          <span><RefreshCcw aria-hidden="true" />Avg Retries</span>
          <strong>{metricValue(module.arc, true)}</strong>
          <small>{module.arc.denominator ? `${module.arc.denominator} completed sessions` : 'Waiting for practice'}</small>
        </div>
      </div>
    </details>
  )
}

export function PerformancePage() {
  const summary = useQuery({
    queryKey: queryKeys.performanceSummary,
    queryFn: performanceApi.summary,
    staleTime: 60_000,
  })

  if (summary.isLoading) return <LoadingState label="Loading performance" description="Calculating your module metrics." variant="page" />
  if (summary.isError) return <ErrorState title="Could not load performance" description={summary.error.message} />

  const data = summary.data!
  const { kpis } = data
  return (
    <main className="performance-page">
      <header className="performance-heading">
        <span>Runebound analytics</span>
        <h1>Performance</h1>
        <p>Track how reliably you solve scenarios, adapt after retries, and handle hard-level challenges.</p>
      </header>

      <section className="performance-kpi-grid" aria-label="Performance indicators">
        <KpiCard label="Scenario Completion" metric={kpis.scr} subtext={`${kpis.scr.numerator}/${kpis.scr.denominator} attempts`} tone="teal" Icon={CircleCheck} />
        <KpiCard label="Command Accuracy" metric={kpis.car} subtext={`${data.completed_sessions} completed attempts`} tone="blue" Icon={Target} />
        <KpiCard label="Hard Completion" metric={kpis.hlcr} subtext={`${kpis.hlcr.numerator}/${kpis.hlcr.denominator} attempts`} tone="neutral" Icon={ShieldCheck} />
        <KpiCard label="Retry Transfer" metric={kpis.rtr} subtext={`${kpis.rtr.numerator}/${kpis.rtr.denominator} attempts`} tone="green" Icon={GitCompareArrows} />
        <KpiCard label="Avg Retry Count" metric={kpis.arc} subtext={`${kpis.arc.denominator} completed sessions`} tone="purple" Icon={RefreshCcw} average />
      </section>

      <section className="performance-modules" aria-labelledby="module-performance-title">
        <header>
          <div className="performance-section-title">
            <ChartNoAxesCombined aria-hidden="true" />
            <h2 id="module-performance-title">Module hard + retry performance</h2>
          </div>
          <div className="performance-summary-strip">
            <span><ShieldCheck aria-hidden="true" />Overall hard completion: <strong>{metricValue(kpis.hlcr)}</strong></span>
            <span><GitCompareArrows aria-hidden="true" />Overall retry transfer: <strong>{metricValue(kpis.rtr)}</strong></span>
            <span><RefreshCcw aria-hidden="true" />Overall avg retries: <strong>{metricValue(kpis.arc, true)}</strong></span>
          </div>
        </header>
        <div className="performance-module-list">
          {data.modules
            .filter((module) => module.number >= 1 && module.number <= 4)
            .map((module) => <ModuleCard key={module.number} module={module} />)}
        </div>
      </section>
    </main>
  )
}
