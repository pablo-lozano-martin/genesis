# Planning Workflow for GitHub Issue #$ARGUMENT$

## Setup Phase
1. Fetch latest branches: `git fetch origin`
2. Get issue details 
   - Fetch issue title: `gh issue view $ARGUMENT$ --json title -q .title`
3. Create a new folder at `doc/features/<issue_title>`

Here are some examples of issue titles and how to name their respective folders:

1. "feature: Add dark mode support for dashboard widgets" -> "Add dark mode support for dashboard widgets" 
2. "bug: Fix login form not validating empty email fields" -> "Fix login form not validating empty email fields"
3. "chore: Update dependencies and remove deprecated APIs" -> "Update dependencies and remove deprecated APIs"

## Analysis Phase
1. Read the full issue content and ALL comments using: `gh issue view $ARGUMENT$ --comments`
2. Analyze the requirements and context thoroughly
3. If any clarifications are needed:
   - List all questions clearly
   - Ask me for answers
   - Post both questions and answers as a comment on the github issue $ARGUMENT$

## Exploration Phase

1. Call the agents who can provide relevant information related to the feature we’re working on.
2. Ensure to provide the feature name, the exact `doc/features/<issue_title>` path and a descriptive prompt that explains the needed task.
3. You MUST call the agents in pararell.
4. Wait for the agents to finish their exploring task.

## Planning Phase

1. Read all files at `doc/features/<issue_title>`.
2. You will see every analysis files made by the agents for this particular task. These files contain curated information on how to approach the feature from each agent’s perspective: plans, conclusions, references to relevant files, etc.
3. Use this valuable information, along with your judgment and skills, to develop a comprehensive and detailed plan that describes exactly how to implement the feature.
4. Write the plan in: `doc/features/<issue_title>/PLAN.md` file.

IMPORTANT: Make sure that the PLAN.md is robust, explicit regarding the implementation and files to change, and contains all the necessary information to carry out the feature.

Once you finish working with the plan, let me know the `doc/features/<issue_title>/PLAN.md` path. I will carefully review it before starting the implementation.