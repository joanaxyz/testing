const LESSON_OVERVIEW_LINE = "The concepts covered in this module's Lesson Overview apply to this scenario."

const MESSAGES: Record<'T1' | 'T2' | 'T3', Record<'easy' | 'medium' | 'hard', string>> = {
  T1: {
    easy: "💡 You've used part of the command budget without reaching the target state. Before the next command, compare the live DAG against the expected state and use diagnostics if you need more context.",
    medium:
      "💡 You're moving beyond the expected command path. Pause, inspect the live DAG against the expected state, and use diagnostics before another action command.",
    hard: '💡 Your current repository state may no longer align with the level objective. Re-read the story and inspect the live DAG before the next command.',
  },
  T2: {
    easy: `⚠️ You've used a significant portion of the command budget and the target state has not been reached. Use the live DAG and expected state to reassess your current repository state. Diagnostics remain free.\n\n${LESSON_OVERVIEW_LINE}`,
    medium: `⚠️ Your command path significantly exceeds the expected transition. Inspect the live DAG carefully and use diagnostics to reassess your repository state.\n\n${LESSON_OVERVIEW_LINE}`,
    hard: `⚠️ Your repository state may have diverged from the objective. Inspect the live DAG and reassess the state transition before continuing.\n\n${LESSON_OVERVIEW_LINE}`,
  },
  T3: {
    easy: `🔴 You are far beyond the expected command path and the target state is still unresolved. If the command limit is reached, the session will fail and a new variant will load on retry. Compare the live DAG against the expected state before the next action command.\n\n${LESSON_OVERVIEW_LINE}`,
    medium: `🔴 Your command path strongly suggests unresolved repository-state divergence. Use free diagnostic commands to inspect the current state before the next action command.\n\n${LESSON_OVERVIEW_LINE}`,
    hard: `🔴 Your repository state remains unresolved despite substantial command usage. Use git log or git reflog to assess the current state before the next action command.\n\n${LESSON_OVERVIEW_LINE}`,
  },
}

export function getScaffoldMessage(
  trigger: 'T1' | 'T2' | 'T3',
  difficulty: 'easy' | 'medium' | 'hard',
): string {
  return MESSAGES[trigger][difficulty]
}
