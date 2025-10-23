# Working with Pablo

## Code Writing

- YOU MUST ALWAYS address me as "Pablo" in all communications.
- We STRONGLY prefer simple, clean, maintainable solutions over clever or complex ones. Readability and maintainability are PRIMARY CONCERNS, even at the cost of conciseness or performance.
- YOU MUST make the SMALLEST reasonable changes to achieve the desired outcome.
- YOU MUST MATCH the style and formatting of surrounding code, even if it differs from standard style guides. Consistency within a file trumps external standards.
- YOU MUST NEVER make code changes unrelated to your current task. If you notice something that should be fixed but is unrelated, document it rather than fixing it immediately.
- YOU MUST NEVER remove code comments unless you can PROVE they are actively false. Comments are important documentation and must be preserved.
- All code files MUST start with a brief 2-line comment explaining what the file does. Each line MUST start with "ABOUTME: " to make them easily greppable.
- YOU MUST NEVER refer to temporal context in comments (like "recently refactored"). Comments should be evergreen and describe the code as it is.
- YOU MUST NEVER implement mock modes for testing or any purpose. We always use real data and real APIs.
- YOU MUST NEVER throw away implementations to rewrite them without EXPLICIT permission. If you're considering this, YOU MUST STOP and ask first.
- YOU MUST NEVER use temporal naming conventions like 'improved', 'new', or 'enhanced'. All naming should be evergreen.
- YOU MUST NOT change whitespace unrelated to code you're modifying.

## Version Control

- For non-trivial edits, all changes MUST be tracked in git.
- If the project isn't in a git repo, YOU MUST STOP and ask permission to initialize one.
- If there are uncommitted changes or untracked files when starting work, YOU MUST STOP and ask how to handle them. Suggest committing existing work first.
- When starting work without a clear branch for the current task, YOU MUST create a WIP branch.
- YOU MUST commit frequently throughout the development process.

## Getting Help

- YOU MUST ALWAYS ask for clarification rather than making assumptions.
- If you're having trouble, YOU MUST STOP and ask for help, especially for tasks where human input would be valuable.

## Agents Workflow

These are the following analyzer agents that you have at your disposal:

- **hexagonal-backend-analyzer** - Backend hexagonal architecture analysis
- **shadcn-ui-analyzer** - React UI components (Shadcn UI & TailwindCSS)
- **api-contract-analyzer** - API endpoints, routes, and schemas
- **data-flow-analyzer** - Data flow across backend layers
- **database-mongodb-analyzer** - MongoDB structure, queries, and performance
- **llm-integration-analyzer** - LLM provider integration patterns
- **react-frontend-analyzer** - React architecture and state management
- **security-analyzer** - Authentication, authorization, and security
- **testing-coverage-analyzer** - Test coverage and strategy

All analyzer agents are for analysis and exploration only. They write findings to `/doc/features/<issue_name>/<analyzer_topic>.md` and NEVER modify code.

NEVER use other agents apart from these.

## Project Documentation

- For general project information, refer to `/doc/general/`:
  - `API.md` - API endpoints reference.
  - `ARCHITECTURE.md` - Hexagonal architecture and design decisions.
  - `DEPLOYMENT.md` - Deployment guide.
  - `DEVELOPMENT.md` - Development workflow and commands.
- These files contain essential context about the project structure, technology stack, and workflows.

## Library Documentation (Context7 MCP)

- YOU MUST ALWAYS use Context7 MCP tools for fetching up-to-date documentation for modern libraries.
- When working with frameworks or libraries (especially LangGraph, LangChain, FastAPI, React, etc.), ALWAYS:
  1. First call `mcp__context7__resolve-library-id` with the library name to get the Context7-compatible ID
  2. Then call `mcp__context7__get-library-docs` with the resolved ID to fetch current documentation
- Context7 provides the most current, accurate documentation including:
  - Code examples and snippets
  - API references
  - Best practices and patterns
  - Up-to-date version-specific guidance
- NEVER rely solely on your training data for library usage patterns - always verify with Context7 first.

## Testing

- Tests MUST comprehensively cover ALL implemented functionality. 
- YOU MUST NEVER ignore system or test output - logs and messages often contain CRITICAL information.
- Test output MUST BE PRISTINE TO PASS.
- If logs are expected to contain errors, these MUST be captured and tested.
- NO EXCEPTIONS POLICY: ALL projects MUST have unit tests, integration tests, AND end-to-end tests. The only way to skip any test type is if Pablo EXPLICITLY states: "I AUTHORIZE YOU TO SKIP WRITING TESTS THIS TIME."

## Compliance Check

Before submitting any work, verify that you have followed ALL guidelines above. If you find yourself considering an exception to ANY rule, YOU MUST STOP and get explicit permission from Pablo first.