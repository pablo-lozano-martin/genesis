// ABOUTME: React hook for WebSocket chat functionality
// ABOUTME: Manages WebSocket connection state, message sending, and streaming reception

import { useState, useEffect, useCallback, useRef } from "react";
import { WebSocketService } from "../services/websocketService";
import type { WebSocketConfig } from "../services/websocketService";

export interface UseWebSocketOptions {
  url: string;
  token: string;
  autoConnect?: boolean;
}

export interface StreamingMessage {
  conversationId: string;
  content: string;
  isComplete: boolean;
}

export interface UseWebSocketReturn {
  isConnected: boolean;
  error: string | null;
  sendMessage: (conversationId: string, content: string) => void;
  streamingMessage: StreamingMessage | null;
  connect: () => void;
  disconnect: () => void;
}

/**
 * Custom hook for WebSocket chat functionality.
 *
 * This hook:
 * - Manages WebSocket connection lifecycle
 * - Handles message sending
 * - Manages streaming message state
 * - Provides connection status and error handling
 * - Auto-reconnects on disconnect
 *
 * @param options - WebSocket configuration options
 * @returns WebSocket state and control functions
 */
export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { url, token, autoConnect = true } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [streamingMessage, setStreamingMessage] = useState<StreamingMessage | null>(null);

  const wsServiceRef = useRef<WebSocketService | null>(null);
  const currentConversationIdRef = useRef<string | null>(null);

  const connect = useCallback(() => {
    if (wsServiceRef.current) {
      wsServiceRef.current.disconnect();
    }

    const config: WebSocketConfig = {
      url,
      token,
      onConnect: () => {
        setIsConnected(true);
        setError(null);
      },
      onDisconnect: () => {
        setIsConnected(false);
        setStreamingMessage(null);
      },
      onToken: (tokenContent: string) => {
        setStreamingMessage((prev) => {
          if (!prev || !currentConversationIdRef.current) {
            return {
              conversationId: currentConversationIdRef.current || "",
              content: tokenContent,
              isComplete: false,
            };
          }
          return {
            ...prev,
            content: prev.content + tokenContent,
          };
        });
      },
      onComplete: (_messageId: string, _conversationId: string) => {
        setStreamingMessage((prev) => {
          if (prev) {
            return {
              ...prev,
              isComplete: true,
            };
          }
          return null;
        });

        setTimeout(() => {
          setStreamingMessage(null);
          currentConversationIdRef.current = null;
        }, 100);
      },
      onError: (errorMessage: string, code?: string) => {
        setError(`${errorMessage}${code ? ` (${code})` : ""}`);
        setStreamingMessage(null);
        currentConversationIdRef.current = null;
      },
    };

    const service = new WebSocketService(config);
    wsServiceRef.current = service;
    service.connect();
  }, [url, token]);

  const disconnect = useCallback(() => {
    if (wsServiceRef.current) {
      wsServiceRef.current.disconnect();
      wsServiceRef.current = null;
    }
    setIsConnected(false);
    setStreamingMessage(null);
    currentConversationIdRef.current = null;
  }, []);

  const sendMessage = useCallback((conversationId: string, content: string) => {
    if (!wsServiceRef.current || !wsServiceRef.current.isConnected()) {
      setError("WebSocket is not connected");
      return;
    }

    currentConversationIdRef.current = conversationId;
    setStreamingMessage({
      conversationId,
      content: "",
      isComplete: false,
    });
    setError(null);

    wsServiceRef.current.sendMessage(conversationId, content);
  }, []);

  useEffect(() => {
    if (autoConnect) {
      connect();
    }

    return () => {
      disconnect();
    };
  }, [autoConnect, connect, disconnect]);

  return {
    isConnected,
    error,
    sendMessage,
    streamingMessage,
    connect,
    disconnect,
  };
}
