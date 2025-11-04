// ABOUTME: Test factory functions for creating mock data
// ABOUTME: Provides consistent mock objects for unit and integration tests

import type { ToolExecution } from "../../contexts/ChatContext";

export function createMockToolExecution(
  overrides?: Partial<ToolExecution>
): ToolExecution {
  return {
    id: `tool-${Date.now()}`,
    toolName: "multiply",
    toolInput: '{"a": 5, "b": 3}',
    toolResult: "15",
    status: "completed",
    startTime: new Date().toISOString(),
    endTime: new Date().toISOString(),
    source: "local",
    ...overrides,
  };
}

export function createMockRunningExecution(
  overrides?: Partial<ToolExecution>
): ToolExecution {
  return createMockToolExecution({
    status: "running",
    toolResult: undefined,
    endTime: undefined,
    ...overrides,
  });
}

export function createMockMCPExecution(
  overrides?: Partial<ToolExecution>
): ToolExecution {
  return createMockToolExecution({
    source: "mcp",
    toolName: "search",
    toolInput: '{"query": "React hooks"}',
    toolResult: "Found documentation at docs.react.dev",
    ...overrides,
  });
}
