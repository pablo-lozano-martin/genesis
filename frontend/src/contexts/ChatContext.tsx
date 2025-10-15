// ABOUTME: Chat context for managing conversation and message state
// ABOUTME: Provides chat state and WebSocket integration to components

import React, { createContext, useContext, useState, useEffect } from "react";
import { useWebSocket } from "../hooks/useWebSocket";
import { conversationService } from "../services/conversationService";
import type { Conversation, Message } from "../services/conversationService";
import { authService } from "../services/authService";

const WS_URL = (import.meta.env.VITE_API_URL || "http://localhost:8000").replace("http", "ws");

interface ChatContextType {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  streamingMessage: string | null;
  isStreaming: boolean;
  isConnected: boolean;
  error: string | null;
  loadConversations: () => Promise<void>;
  createConversation: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => void;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [streamingMessage, setStreamingMessage] = useState<string | null>(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const token = authService.getToken() || "";
  const { isConnected, error, sendMessage: wsSendMessage, streamingMessage: wsStreamingMessage } = useWebSocket({
    url: `${WS_URL}/ws/chat`,
    token,
    autoConnect: true,
  });

  useEffect(() => {
    if (wsStreamingMessage) {
      setStreamingMessage(wsStreamingMessage.content);
      setIsStreaming(!wsStreamingMessage.isComplete);

      if (wsStreamingMessage.isComplete) {
        setTimeout(() => {
          setStreamingMessage(null);
          if (currentConversation) {
            loadMessages(currentConversation.id);
          }
        }, 100);
      }
    }
  }, [wsStreamingMessage]);

  const loadConversations = async () => {
    try {
      const convs = await conversationService.listConversations();
      setConversations(convs);
    } catch (err) {
      console.error("Failed to load conversations:", err);
    }
  };

  const createConversation = async () => {
    try {
      const newConv = await conversationService.createConversation({ title: "New Chat" });
      setConversations((prev) => [newConv, ...prev]);
      setCurrentConversation(newConv);
      setMessages([]);
    } catch (err) {
      console.error("Failed to create conversation:", err);
    }
  };

  const loadMessages = async (conversationId: string) => {
    try {
      const msgs = await conversationService.getMessages(conversationId);
      setMessages(msgs);
    } catch (err) {
      console.error("Failed to load messages:", err);
    }
  };

  const selectConversation = async (id: string) => {
    try {
      const conv = await conversationService.getConversation(id);
      setCurrentConversation(conv);
      await loadMessages(id);
    } catch (err) {
      console.error("Failed to select conversation:", err);
    }
  };

  const deleteConversation = async (id: string) => {
    try {
      await conversationService.deleteConversation(id);
      setConversations((prev) => prev.filter((c) => c.id !== id));
      if (currentConversation?.id === id) {
        setCurrentConversation(null);
        setMessages([]);
      }
    } catch (err) {
      console.error("Failed to delete conversation:", err);
    }
  };

  const sendMessage = (content: string) => {
    if (!currentConversation || !isConnected) return;

    setMessages((prev) => [
      ...prev,
      {
        id: `temp-${Date.now()}`,
        conversation_id: currentConversation.id,
        role: "user",
        content,
        created_at: new Date().toISOString(),
      },
    ]);

    setIsStreaming(true);
    wsSendMessage(currentConversation.id, content);
  };

  useEffect(() => {
    loadConversations();
  }, []);

  return (
    <ChatContext.Provider
      value={{
        conversations,
        currentConversation,
        messages,
        streamingMessage,
        isStreaming,
        isConnected,
        error,
        loadConversations,
        createConversation,
        selectConversation,
        deleteConversation,
        sendMessage,
      }}
    >
      {children}
    </ChatContext.Provider>
  );
};

export const useChat = () => {
  const context = useContext(ChatContext);
  if (!context) {
    throw new Error("useChat must be used within ChatProvider");
  }
  return context;
};
