// ABOUTME: Integration tests for MessageList tool card rendering and interaction
// ABOUTME: Tests accordion behavior and tool card rendering within MessageList

import { describe, it, expect, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MessageList } from "../../../../components/chat/MessageList";
import {
  createMockToolExecution,
  createMockRunningExecution,
  createMockMCPExecution,
} from "../../../utils/test-factories";

describe("MessageList Tool Cards Integration", () => {
  const defaultProps = {
    messages: [],
    streamingMessage: null,
    isStreaming: false,
    toolExecutions: [],
    expandedToolId: null,
    onToggleExpandTool: vi.fn(),
  };

  describe("Rendering", () => {
    it("renders no tool cards when toolExecutions is empty", () => {
      render(<MessageList {...defaultProps} />);

      expect(screen.queryByRole("img", { hidden: true })).not.toBeInTheDocument();
    });

    it("renders one card when toolExecutions has one execution", () => {
      const execution = createMockToolExecution({ toolName: "multiply" });

      render(
        <MessageList {...defaultProps} toolExecutions={[execution]} />
      );

      expect(screen.getByText("multiply")).toBeInTheDocument();
    });

    it("renders multiple cards when toolExecutions has multiple executions", () => {
      const executions = [
        createMockToolExecution({ id: "tool-1", toolName: "multiply" }),
        createMockToolExecution({ id: "tool-2", toolName: "divide" }),
        createMockToolExecution({ id: "tool-3", toolName: "add" }),
      ];

      render(
        <MessageList {...defaultProps} toolExecutions={executions} />
      );

      expect(screen.getByText("multiply")).toBeInTheDocument();
      expect(screen.getByText("divide")).toBeInTheDocument();
      expect(screen.getByText("add")).toBeInTheDocument();
    });
  });

  describe("Accordion Behavior", () => {
    it("passes correct isExpanded prop to first card when expandedToolId matches", () => {
      const execution = createMockToolExecution({
        id: "tool-1",
        toolName: "multiply",
      });

      render(
        <MessageList
          {...defaultProps}
          toolExecutions={[execution]}
          expandedToolId="tool-1"
        />
      );

      expect(screen.getByText("Arguments")).toBeInTheDocument();
    });

    it("does not expand card when expandedToolId does not match", () => {
      const execution = createMockToolExecution({
        id: "tool-1",
        toolName: "multiply",
      });

      render(
        <MessageList
          {...defaultProps}
          toolExecutions={[execution]}
          expandedToolId="tool-2"
        />
      );

      expect(screen.queryByText("Arguments")).not.toBeInTheDocument();
    });

    it("only expands one card at a time", () => {
      const executions = [
        createMockToolExecution({ id: "tool-1", toolName: "multiply" }),
        createMockToolExecution({ id: "tool-2", toolName: "divide" }),
      ];

      render(
        <MessageList
          {...defaultProps}
          toolExecutions={executions}
          expandedToolId="tool-1"
        />
      );

      const argumentsSections = screen.queryAllByText("Arguments");
      expect(argumentsSections).toHaveLength(1);
    });
  });

  describe("Click Interactions", () => {
    it("calls onToggleExpandTool with correct id when card clicked", async () => {
      const onToggleExpandTool = vi.fn();
      const execution = createMockToolExecution({ id: "tool-1" });
      const user = userEvent.setup();

      const { container } = render(
        <MessageList
          {...defaultProps}
          toolExecutions={[execution]}
          onToggleExpandTool={onToggleExpandTool}
        />
      );

      const header = container.querySelector(".hover\\:opacity-80");
      if (header) {
        await user.click(header);
      }

      expect(onToggleExpandTool).toHaveBeenCalledWith("tool-1");
    });

    it("calls onToggleExpandTool when clicking second card", async () => {
      const onToggleExpandTool = vi.fn();
      const executions = [
        createMockToolExecution({ id: "tool-1", toolName: "multiply" }),
        createMockToolExecution({ id: "tool-2", toolName: "divide" }),
      ];
      const user = userEvent.setup();

      const { container } = render(
        <MessageList
          {...defaultProps}
          toolExecutions={executions}
          onToggleExpandTool={onToggleExpandTool}
        />
      );

      const headers = container.querySelectorAll(".hover\\:opacity-80");
      if (headers[1]) {
        await user.click(headers[1]);
      }

      expect(onToggleExpandTool).toHaveBeenCalledWith("tool-2");
    });
  });

  describe("Dynamic Updates", () => {
    it("adds new card when execution added to array", () => {
      const execution1 = createMockToolExecution({ toolName: "multiply" });
      const { rerender } = render(
        <MessageList {...defaultProps} toolExecutions={[execution1]} />
      );

      expect(screen.getByText("multiply")).toBeInTheDocument();
      expect(screen.queryByText("divide")).not.toBeInTheDocument();

      const execution2 = createMockToolExecution({ toolName: "divide" });
      rerender(
        <MessageList {...defaultProps} toolExecutions={[execution1, execution2]} />
      );

      expect(screen.getByText("multiply")).toBeInTheDocument();
      expect(screen.getByText("divide")).toBeInTheDocument();
    });

    it("updates card status when execution status changes", () => {
      const runningExecution = createMockRunningExecution({ id: "tool-1" });
      const { rerender, container } = render(
        <MessageList {...defaultProps} toolExecutions={[runningExecution]} />
      );

      expect(container.querySelector(".animate-spin")).toBeInTheDocument();

      const completedExecution = createMockToolExecution({ id: "tool-1" });
      rerender(
        <MessageList {...defaultProps} toolExecutions={[completedExecution]} />
      );

      expect(container.querySelector(".animate-spin")).not.toBeInTheDocument();
    });
  });

  describe("Mixed Tool Types", () => {
    it("renders both local and MCP tools correctly", () => {
      const executions = [
        createMockToolExecution({ id: "tool-1", source: "local" }),
        createMockMCPExecution({ id: "tool-2" }),
      ];

      render(
        <MessageList {...defaultProps} toolExecutions={executions} />
      );

      expect(screen.getByText("MCP")).toBeInTheDocument();
      const mcpBadges = screen.queryAllByText("MCP");
      expect(mcpBadges).toHaveLength(1);
    });
  });

  describe("Scrolling Behavior", () => {
    it("component includes scroll reference for auto-scroll", () => {
      const { container } = render(<MessageList {...defaultProps} />);

      const scrollRef = container.querySelector(".flex-1.overflow-y-auto");
      expect(scrollRef).toBeInTheDocument();
    });
  });
});
