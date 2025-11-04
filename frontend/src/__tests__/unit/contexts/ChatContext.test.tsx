// ABOUTME: Unit tests for ChatContext tool execution logic
// ABOUTME: Tests tool start, complete, persistence, and accordion state management

import { describe, it, expect, vi, beforeEach } from "vitest";
import { renderHook, act, waitFor } from "@testing-library/react";
import { ChatProvider, useChat } from "../../../contexts/ChatContext";
import type { ReactNode } from "react";

// Mock services and hooks
vi.mock("../../../hooks/useWebSocket", () => ({
  useWebSocket: vi.fn(() => ({
    isConnected: true,
    error: null,
    sendMessage: vi.fn(),
    streamingMessage: null,
  })),
}));

vi.mock("../../../services/conversationService", () => ({
  conversationService: {
    listConversations: vi.fn(() => Promise.resolve([])),
    createConversation: vi.fn(() =>
      Promise.resolve({ id: "conv-1", title: "New Chat", created_at: new Date().toISOString() })
    ),
    getConversation: vi.fn(() =>
      Promise.resolve({ id: "conv-1", title: "Test Conv", created_at: new Date().toISOString() })
    ),
    getMessages: vi.fn(() => Promise.resolve([])),
    deleteConversation: vi.fn(() => Promise.resolve()),
    updateConversation: vi.fn((id, data) =>
      Promise.resolve({ id, ...data, created_at: new Date().toISOString() })
    ),
  },
}));

vi.mock("../../../services/authService", () => ({
  authService: {
    getToken: vi.fn(() => "mock-token"),
  },
}));

const wrapper = ({ children }: { children: ReactNode }) => (
  <ChatProvider>{children}</ChatProvider>
);

describe("ChatContext Tool Execution", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("Initial State", () => {
    it("initializes with empty toolExecutions array", () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      expect(result.current.toolExecutions).toEqual([]);
    });

    it("initializes with null currentToolExecution", () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      expect(result.current.currentToolExecution).toBeNull();
    });

    it("initializes with null expandedToolId", () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      expect(result.current.expandedToolId).toBeNull();
    });
  });

  describe("setExpandedToolId", () => {
    it("updates expandedToolId state", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      act(() => {
        result.current.setExpandedToolId("tool-123");
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBe("tool-123");
      });
    });

    it("can set expandedToolId to null", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      act(() => {
        result.current.setExpandedToolId("tool-123");
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBe("tool-123");
      });

      act(() => {
        result.current.setExpandedToolId(null);
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBeNull();
      });
    });
  });

  describe("Tool Execution Persistence", () => {
    it("does not clear toolExecutions on stream completion", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });
      const { useWebSocket } = await import("../../../hooks/useWebSocket");
      const mockUseWebSocket = vi.mocked(useWebSocket);

      await act(async () => {
        await result.current.createConversation();
      });

      const wsOnToolStart = mockUseWebSocket.mock.results[0]?.value.onToolStart;
      if (wsOnToolStart) {
        act(() => {
          wsOnToolStart("multiply", '{"a": 5, "b": 3}', "local");
        });
      }

      await waitFor(() => {
        expect(result.current.toolExecutions.length).toBe(1);
      });

      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        error: null,
        sendMessage: vi.fn(),
        streamingMessage: {
          content: "The result is 15",
          isComplete: true,
        },
      });

      await waitFor(() => {
        expect(result.current.toolExecutions.length).toBe(1);
      });
    });
  });

  describe("Stream Completion", () => {
    it("sets expandedToolId to null on stream completion", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });
      const { useWebSocket } = await import("../../../hooks/useWebSocket");
      const mockUseWebSocket = vi.mocked(useWebSocket);

      await act(async () => {
        await result.current.createConversation();
      });

      act(() => {
        result.current.setExpandedToolId("tool-123");
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBe("tool-123");
      });

      mockUseWebSocket.mockReturnValue({
        isConnected: true,
        error: null,
        sendMessage: vi.fn(),
        streamingMessage: {
          content: "Done",
          isComplete: true,
        },
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBeNull();
      });
    });
  });

  describe("Conversation Selection", () => {
    it("clears toolExecutions when selecting conversation", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });
      const { useWebSocket } = await import("../../../hooks/useWebSocket");
      const mockUseWebSocket = vi.mocked(useWebSocket);

      await act(async () => {
        await result.current.createConversation();
      });

      const wsOnToolStart = mockUseWebSocket.mock.results[0]?.value.onToolStart;
      if (wsOnToolStart) {
        act(() => {
          wsOnToolStart("multiply", '{"a": 5}', "local");
        });
      }

      await waitFor(() => {
        expect(result.current.toolExecutions.length).toBe(1);
      });

      await act(async () => {
        await result.current.selectConversation("conv-2");
      });

      await waitFor(() => {
        expect(result.current.toolExecutions).toEqual([]);
      });
    });

    it("clears expandedToolId when selecting conversation", async () => {
      const { result } = renderHook(() => useChat(), { wrapper });

      await act(async () => {
        await result.current.createConversation();
      });

      act(() => {
        result.current.setExpandedToolId("tool-123");
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBe("tool-123");
      });

      await act(async () => {
        await result.current.selectConversation("conv-2");
      });

      await waitFor(() => {
        expect(result.current.expandedToolId).toBeNull();
      });
    });
  });
});
