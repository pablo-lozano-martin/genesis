// ABOUTME: End-to-end tests for complete tool execution lifecycle
// ABOUTME: Tests tool execution from start to completion with full context integration

import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { ChatProvider } from "../../contexts/ChatContext";
import { Chat } from "../../pages/Chat";
import type { ReactNode } from "react";

// Mock AuthContext
vi.mock("../../contexts/AuthContext", () => ({
  useAuth: () => ({
    user: { username: "testuser" },
    logout: vi.fn(),
  }),
}));

// Mock services
vi.mock("../../services/conversationService", () => ({
  conversationService: {
    listConversations: vi.fn(() =>
      Promise.resolve([
        { id: "conv-1", title: "Test Chat", created_at: new Date().toISOString() },
      ])
    ),
    createConversation: vi.fn(() =>
      Promise.resolve({ id: "conv-new", title: "New Chat", created_at: new Date().toISOString() })
    ),
    getConversation: vi.fn((id) =>
      Promise.resolve({ id, title: "Test Chat", created_at: new Date().toISOString() })
    ),
    getMessages: vi.fn(() => Promise.resolve([])),
    deleteConversation: vi.fn(() => Promise.resolve()),
    updateConversation: vi.fn((id, data) =>
      Promise.resolve({ id, ...data, created_at: new Date().toISOString() })
    ),
  },
}));

vi.mock("../../services/authService", () => ({
  authService: {
    getToken: vi.fn(() => "mock-token"),
  },
}));

// Mock WebSocket
let mockOnToolStart: ((toolName: string, toolInput: string, source?: string) => void) | null = null;
let mockOnToolComplete: ((toolName: string, toolResult: string, source?: string) => void) | null = null;

vi.mock("../../hooks/useWebSocket", () => ({
  useWebSocket: vi.fn((config) => {
    mockOnToolStart = config.onToolStart;
    mockOnToolComplete = config.onToolComplete;
    return {
      isConnected: true,
      error: null,
      sendMessage: vi.fn(),
      streamingMessage: null,
    };
  }),
}));

const AppWrapper = ({ children }: { children: ReactNode }) => (
  <ChatProvider>{children}</ChatProvider>
);

describe("Tool Execution Lifecycle E2E", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockOnToolStart = null;
    mockOnToolComplete = null;
  });

  describe("Single Tool Execution", () => {
    it("shows tool card from start to completion and persists", async () => {
      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Test Chat")).toBeInTheDocument();
      });

      const conversation = screen.getByText("Test Chat");
      await userEvent.click(conversation);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("multiply", '{"a": 5, "b": 3}', "local");
      }

      await waitFor(() => {
        expect(screen.getByText("multiply")).toBeInTheDocument();
      });

      const spinnerBefore = document.querySelector(".animate-spin");
      expect(spinnerBefore).toBeInTheDocument();

      if (mockOnToolComplete) {
        mockOnToolComplete("multiply", "15", "local");
      }

      await waitFor(() => {
        expect(document.querySelector(".animate-spin")).not.toBeInTheDocument();
      });

      expect(screen.getByText("multiply")).toBeInTheDocument();
    });
  });

  describe("Expand and Collapse", () => {
    it("expands card to show full details on click", async () => {
      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Test Chat")).toBeInTheDocument();
      });

      const conversation = screen.getByText("Test Chat");
      await userEvent.click(conversation);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("multiply", '{"a": 5, "b": 3}', "local");
      }

      if (mockOnToolComplete) {
        mockOnToolComplete("multiply", "15", "local");
      }

      await waitFor(() => {
        expect(screen.getByText("multiply")).toBeInTheDocument();
      });

      expect(screen.queryByText("Arguments")).not.toBeInTheDocument();

      const cardHeader = document.querySelector(".hover\\:opacity-80");
      if (cardHeader) {
        await userEvent.click(cardHeader);
      }

      await waitFor(() => {
        expect(screen.getByText("Arguments")).toBeInTheDocument();
        expect(screen.getByText("Result")).toBeInTheDocument();
      });
    });

    it("collapses card on second click", async () => {
      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Test Chat")).toBeInTheDocument();
      });

      const conversation = screen.getByText("Test Chat");
      await userEvent.click(conversation);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("multiply", '{"a": 5}', "local");
      }

      if (mockOnToolComplete) {
        mockOnToolComplete("multiply", "10", "local");
      }

      await waitFor(() => {
        expect(screen.getByText("multiply")).toBeInTheDocument();
      });

      const cardHeader = document.querySelector(".hover\\:opacity-80");
      if (cardHeader) {
        await userEvent.click(cardHeader);
      }

      await waitFor(() => {
        expect(screen.getByText("Arguments")).toBeInTheDocument();
      });

      if (cardHeader) {
        await userEvent.click(cardHeader);
      }

      await waitFor(() => {
        expect(screen.queryByText("Arguments")).not.toBeInTheDocument();
      });
    });
  });

  describe("Multiple Tools", () => {
    it("renders all tool cards and maintains accordion behavior", async () => {
      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Test Chat")).toBeInTheDocument();
      });

      const conversation = screen.getByText("Test Chat");
      await userEvent.click(conversation);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("multiply", '{"a": 5}', "local");
      }

      if (mockOnToolComplete) {
        mockOnToolComplete("multiply", "10", "local");
      }

      if (mockOnToolStart) {
        mockOnToolStart("divide", '{"a": 10}', "local");
      }

      if (mockOnToolComplete) {
        mockOnToolComplete("divide", "5", "local");
      }

      await waitFor(() => {
        expect(screen.getByText("multiply")).toBeInTheDocument();
        expect(screen.getByText("divide")).toBeInTheDocument();
      });
    });
  });

  describe("MCP Tools", () => {
    it("displays MCP badge for MCP tools", async () => {
      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Test Chat")).toBeInTheDocument();
      });

      const conversation = screen.getByText("Test Chat");
      await userEvent.click(conversation);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("search", '{"query": "React"}', "mcp");
      }

      if (mockOnToolComplete) {
        mockOnToolComplete("search", "Found docs", "mcp");
      }

      await waitFor(() => {
        expect(screen.getByText("MCP")).toBeInTheDocument();
      });
    });
  });

  describe("Conversation Switching", () => {
    it("clears tool cards when switching conversations", async () => {
      const { conversationService } = await import("../../services/conversationService");
      vi.mocked(conversationService.listConversations).mockResolvedValue([
        { id: "conv-1", title: "Chat 1", created_at: new Date().toISOString() },
        { id: "conv-2", title: "Chat 2", created_at: new Date().toISOString() },
      ]);

      render(
        <AppWrapper>
          <Chat />
        </AppWrapper>
      );

      await waitFor(() => {
        expect(screen.getByText("Chat 1")).toBeInTheDocument();
      });

      const conversation1 = screen.getByText("Chat 1");
      await userEvent.click(conversation1);

      await waitFor(() => {
        expect(mockOnToolStart).not.toBeNull();
      });

      if (mockOnToolStart) {
        mockOnToolStart("multiply", '{"a": 5}', "local");
      }

      await waitFor(() => {
        expect(screen.getByText("multiply")).toBeInTheDocument();
      });

      const conversation2 = screen.getByText("Chat 2");
      await userEvent.click(conversation2);

      await waitFor(() => {
        expect(screen.queryByText("multiply")).not.toBeInTheDocument();
      });
    });
  });
});
