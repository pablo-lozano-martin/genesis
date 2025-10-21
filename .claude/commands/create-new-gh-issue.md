# Create New GitHub Issue for Feature

## Input
Feature/Bug/Chore idea: $ARGUMENT$

## Step 1: Analysis
- Analyze the feature/bug/chore idea provided
- Look at relevant code files to understand current implementation
- Identify what needs clarification

## Step 2: Clarification
Ask me questions about anything unclear:
- User scenarios
- Edge cases
- Integration requirements
- Performance needs
- Dependencies

For each question, include 3 suggested options (with A/B/C format). Wait for my answers before continuing.

## Step 3: Draft Issue
Create an issue with this structure:

### Problem Statement
What problem does this solve? What are current limitations?

### User Value
What specific benefits will users get? Give concrete examples.

### Definition of Done
- Implementation complete with edge cases handled
- Unit tests added (>80% coverage)
- Integration tests for main flows
- Documentation updated
- Code review approved
- CI/CD passes
- Manual testing complete

### Manual Testing Checklist
- Basic flow: [specific steps]
- Edge case testing: [specific scenarios]
- Error handling: [error scenarios to test]
- Integration: [test with existing features]

## Step 4: Review
Show me the complete issue draft and ask: "Is this ready to create? Any changes needed?"

Wait for my approval.

## Step 5: Create Issue
After approval, run:
```
gh issue create --title "feature/bug/chore: YOUR_TITLE_HERE" --body "YOUR_ISSUE_CONTENT_HERE"
```

Here are some examples of issue titles so you can know the expected format:

1. "feature: Add dark mode support for dashboard widgets"
2. "bug: Fix login form not validating empty email fields"
3. "chore: Update dependencies and remove deprecated APIs"

Tell me the issue number and URL when done.

## Remember
- Check actual code before suggesting solutions
- Use specific file names and paths
- Make testing steps concrete and actionable
- Focus on user benefits, not technical details
- Triage and use the correct term in the issue: it's a feature, a bug or a chore?