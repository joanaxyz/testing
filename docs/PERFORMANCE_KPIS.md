# Performance KPI definitions

The authenticated `GET /api/progress/performance/` endpoint is the source of
truth for The Runebound Turret's overall and per-module performance metrics.
All attempt-based metrics exclude replay runs.

| KPI | Formula | Empty-data behavior |
| --- | --- | --- |
| Scenario Completion Rate (SCR) | completed attempts / all attempts | `value: null` when there are no attempts |
| Command Accuracy Rate (CAR) | processable submitted commands / all submitted commands | `value: null` when there are no commands |
| Hard-Level Completion Rate (HLCR) | completed hard attempts / all hard attempts | `value: null` when there are no hard attempts |
| Retry Transfer Rate (RTR) | completed retry attempts / all retry attempts | `value: null` when there are no retry attempts |
| Average Retry Count (ARC) | sum of `retry_index` for completed attempts / completed attempts | `value: null` when there are no completed attempts |

A retry attempt is a run with `prior_run` set. CAR treats `Invalid` and
`Unprocessable` command results as inaccurate; every other submitted command
is processable. The response includes Modules 0–4 even when a module has no
attempts so the frontend can present an honest “Waiting for practice” state.
