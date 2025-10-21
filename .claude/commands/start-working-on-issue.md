# GitHub Issue Workflow for Issue #$ARGUMENT$

## Setup Phase
1. Fetch latest branches: `git fetch origin`
2. Get issue details 
   - Fetch issue title: `gh issue view $ARGUMENT$ --json title -q .title`
3. Read `doc/features/<issue_title>/PLAN.md` file.

Here are some examples of issue titles and how their respective folders are named:

1. "feature: Add dark mode support for dashboard widgets" -> "Add dark mode support for dashboard widgets" 
2. "bug: Fix login form not validating empty email fields" -> "Fix login form not validating empty email fields"
3. "chore: Update dependencies and remove deprecated APIs" -> "Update dependencies and remove deprecated APIs"

## Implementation Phase
1. Execute the plan step by step, remember to build test before the implementation and run the test suite constanly to get quick feedback.
2. Ensure consistency with existing code in the branch
3. Run local builds and tests suite before git commit & push
4. create the PR
5. Report status of completenes:

<results>

  # Summary of the requirements implemented:
	- req 1
        - req 2
	- ...

  # Requirements pending
	- req 1
        - req 2
	- ...
  # Test implemented and their run status
     ok    github.com/drinksilver/scoop/internal/testing/blalb_test.go       31.604sm

  # Proof that all build passes
     ok    github.com/drinksilver/scoop/internal/testing/e2e       31.604sm
     ok    github.com/drinksilver/scoop/internal       90.604sm
  
  # Overall status: [Needs More Work/All Completed]
  # PR: github-pr-url
</result>

## Important Notes
- The All completed is the desired status and we can only arrive if we have implemented all the requirements and all the test suite are implemented and green otherwhise we need more work until that happends
- Always use `gh` CLI for GitHub operations
- Keep detailed records of all actions as PR/issue comments
- Wait for explicit confirmation before proceeding with major changes