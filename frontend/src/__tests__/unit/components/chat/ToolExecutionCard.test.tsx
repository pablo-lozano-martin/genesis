// ABOUTME: Unit tests for ToolExecutionCard component
// ABOUTME: Tests rendering, expansion, icons, badges, and formatting

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ToolExecutionCard } from "../../../../components/chat/ToolExecutionCard";
import {
  createMockToolExecution,
  createMockRunningExecution,
  createMockMCPExecution,
} from "../../../utils/test-factories";

describe("ToolExecutionCard", () => {
  describe("Status Icons", () => {
    it("renders Loader2 icon when status is running", () => {
      const execution = createMockRunningExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      const loader = document.querySelector(".animate-spin");
      expect(loader).toBeInTheDocument();
    });

    it("renders Check icon when status is completed", () => {
      const execution = createMockToolExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByRole("img", { hidden: true })).toBeInTheDocument();
    });
  });

  describe("Badges", () => {
    it("displays tool name badge for local tool", () => {
      const execution = createMockToolExecution({ toolName: "multiply" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("multiply")).toBeInTheDocument();
    });

    it("displays MCP badge for MCP tool", () => {
      const execution = createMockMCPExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("MCP")).toBeInTheDocument();
    });

    it("does not display MCP badge for local tool", () => {
      const execution = createMockToolExecution({ source: "local" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText("MCP")).not.toBeInTheDocument();
    });
  });

  describe("Collapsed State", () => {
    it("shows result preview when collapsed and completed", () => {
      const execution = createMockToolExecution({ toolResult: "42" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("→ 42")).toBeInTheDocument();
    });

    it("does not show result preview when expanded", () => {
      const execution = createMockToolExecution({ toolResult: "42" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText("→ 42")).not.toBeInTheDocument();
    });

    it("does not show arguments or result details when collapsed", () => {
      const execution = createMockToolExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText("Arguments")).not.toBeInTheDocument();
      expect(screen.queryByText("Result")).not.toBeInTheDocument();
    });
  });

  describe("Expanded State", () => {
    it("shows Arguments section when expanded", () => {
      const execution = createMockToolExecution({
        toolInput: '{"a": 5, "b": 3}',
      });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("Arguments")).toBeInTheDocument();
    });

    it("shows Result section when expanded", () => {
      const execution = createMockToolExecution({ toolResult: "15" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("Result")).toBeInTheDocument();
    });

    it("shows timing information when expanded and completed", () => {
      const execution = createMockToolExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText(/Started:/)).toBeInTheDocument();
      expect(screen.getByText(/Duration:/)).toBeInTheDocument();
    });

    it("does not show timing information when running", () => {
      const execution = createMockRunningExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText(/Started:/)).not.toBeInTheDocument();
      expect(screen.queryByText(/Duration:/)).not.toBeInTheDocument();
    });
  });

  describe("Chevron Icon", () => {
    it("renders chevron pointing down when collapsed", () => {
      const execution = createMockToolExecution();
      const onToggleExpand = vi.fn();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      const chevron = container.querySelector(".transition-transform");
      expect(chevron).toBeInTheDocument();
      expect(chevron?.className).not.toContain("rotate-180");
    });

    it("renders chevron rotated when expanded", () => {
      const execution = createMockToolExecution();
      const onToggleExpand = vi.fn();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      const chevron = container.querySelector(".transition-transform");
      expect(chevron?.className).toContain("rotate-180");
    });
  });

  describe("Click Handler", () => {
    it("calls onToggleExpand with correct id when header clicked", async () => {
      const execution = createMockToolExecution({ id: "tool-123" });
      const onToggleExpand = vi.fn();
      const user = userEvent.setup();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      const header = container.querySelector(".hover\\:opacity-80");
      if (header) {
        await user.click(header);
      }

      expect(onToggleExpand).toHaveBeenCalledWith("tool-123");
      expect(onToggleExpand).toHaveBeenCalledTimes(1);
    });
  });

  describe("JSON Formatting", () => {
    it("formats valid JSON with indentation", () => {
      const execution = createMockToolExecution({
        toolInput: '{"a":5,"b":3}',
      });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      const formatted = screen.getByText(/{\s+"a": 5,\s+"b": 3\s+}/);
      expect(formatted).toBeInTheDocument();
    });

    it("displays invalid JSON as-is without formatting", () => {
      const execution = createMockToolExecution({
        toolInput: "not json",
      });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText("not json")).toBeInTheDocument();
    });
  });

  describe("Duration Calculation", () => {
    it("displays duration in milliseconds when < 1000ms", () => {
      const startTime = new Date("2025-01-01T10:00:00.000Z").toISOString();
      const endTime = new Date("2025-01-01T10:00:00.500Z").toISOString();
      const execution = createMockToolExecution({ startTime, endTime });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText(/Duration: 500ms/)).toBeInTheDocument();
    });

    it("displays duration in seconds when >= 1000ms", () => {
      const startTime = new Date("2025-01-01T10:00:00.000Z").toISOString();
      const endTime = new Date("2025-01-01T10:00:01.230Z").toISOString();
      const execution = createMockToolExecution({ startTime, endTime });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.getByText(/Duration: 1.23s/)).toBeInTheDocument();
    });
  });

  describe("Dark Mode Classes", () => {
    it("applies dark mode classes for local tool", () => {
      const execution = createMockToolExecution({ source: "local" });
      const onToggleExpand = vi.fn();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      const card = container.querySelector(".border-l-blue-500");
      expect(card?.className).toContain("dark:border-l-blue-400");
      expect(card?.className).toContain("dark:bg-blue-950/30");
    });

    it("applies dark mode classes for MCP tool", () => {
      const execution = createMockMCPExecution();
      const onToggleExpand = vi.fn();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={false}
          onToggleExpand={onToggleExpand}
        />
      );

      const card = container.querySelector(".border-l-purple-500");
      expect(card?.className).toContain("dark:border-l-purple-400");
      expect(card?.className).toContain("dark:bg-purple-950/30");
    });
  });

  describe("Edge Cases", () => {
    it("handles empty toolInput gracefully", () => {
      const execution = createMockToolExecution({ toolInput: "" });
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText("Arguments")).not.toBeInTheDocument();
    });

    it("handles undefined toolResult gracefully", () => {
      const execution = createMockRunningExecution();
      const onToggleExpand = vi.fn();

      render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      expect(screen.queryByText("Result")).not.toBeInTheDocument();
    });

    it("applies max-height to result section", () => {
      const execution = createMockToolExecution({
        toolResult: "x".repeat(10000),
      });
      const onToggleExpand = vi.fn();

      const { container } = render(
        <ToolExecutionCard
          execution={execution}
          isExpanded={true}
          onToggleExpand={onToggleExpand}
        />
      );

      const resultContainer = container.querySelector(".overflow-y-auto");
      expect(resultContainer).toHaveStyle({ maxHeight: "500px" });
    });
  });
});
