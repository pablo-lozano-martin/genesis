// ABOUTME: Chat context for managing conversation and message state
// ABOUTME: Provides chat state and REST API integration to components

import React, { createContext, useContext, useState, useEffect, useCallback } from "react";
import { conversationService } from "../services/conversationService";
import type { Conversation, Message } from "../services/conversationService";
import { generateTitleFromMessage } from "../lib/titleUtils";

interface ChatContextType {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isMessageLoading: boolean;
  error: string | null;
  loadConversations: () => Promise<void>;
  createConversation: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  deleteConversation: (id: string) => Promise<void>;
  sendMessage: (content: string) => void;
  updateConversationTitle: (id: string, title: string) => Promise<void>;
}

const ChatContext = createContext<ChatContextType | undefined>(undefined);

export const ChatProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversation, setCurrentConversation] = useState<Conversation | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [isMessageLoading, setIsMessageLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

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

  const updateConversationTitle = async (id: string, title: string) => {
    try {
      const updated = await conversationService.updateConversation(id, { title });

      // Update conversations list
      setConversations((prev) =>
        prev.map((c) => (c.id === id ? updated : c))
      );

      // Update current conversation if it's the one being renamed
      if (currentConversation?.id === id) {
        setCurrentConversation(updated);
      }
    } catch (err) {
      console.error("Failed to update conversation title:", err);
    }
  };

  const sendMessage = useCallback(
    async (content: string) => {
      if (!currentConversation || isMessageLoading) return;

      setIsMessageLoading(true);
      setError(null);

      try {
        const { user_message, assistant_message } = await conversationService.sendMessage(
          currentConversation.id,
          content
        );

        setMessages((prev) => [...prev, user_message, assistant_message]);

        // Auto-generate title on first message
        if (currentConversation.message_count === 0) {
          const newTitle = generateTitleFromMessage(content);
          await updateConversationTitle(currentConversation.id, newTitle);
        }

        await loadConversations();
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to send message");
      } finally {
        setIsMessageLoading(false);
      }
    },
    [currentConversation, isMessageLoading]
  );

  useEffect(() => {
    loadConversations();
  }, []);

  return (
    <ChatContext.Provider
      value={{
        conversations,
        currentConversation,
        messages,
        isMessageLoading,
        error,
        loadConversations,
        createConversation,
        selectConversation,
        deleteConversation,
        sendMessage,
        updateConversationTitle,
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
