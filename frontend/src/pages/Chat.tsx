// ABOUTME: Main chat page bringing together all chat components
// ABOUTME: Clean, minimal layout focused on chatting

import React from "react";
import { useChat } from "../contexts/ChatContext";
import { useAuth } from "../contexts/AuthContext";
import { MessageList } from "../components/chat/MessageList";
import { MessageInput } from "../components/chat/MessageInput";
import { ConversationSidebar } from "../components/chat/ConversationSidebar";
import { ThemeToggle } from "../components/ThemeToggle";

export const Chat: React.FC = () => {
  const { user, logout } = useAuth();
  const {
    conversations,
    currentConversation,
    messages,
    streamingMessage,
    isStreaming,
    isConnected,
    error,
    toolExecutions,
    expandedToolId,
    setExpandedToolId,
    createConversation,
    selectConversation,
    deleteConversation,
    sendMessage,
    updateConversationTitle,
  } = useChat();

  return (
    <div className="h-screen flex flex-col">
      <div className="border-b dark:border-gray-700 px-4 py-3 flex items-center justify-between bg-white dark:bg-gray-800">
        <div className="font-semibold dark:text-white">Genesis</div>
        <div className="flex items-center gap-4">
          <ThemeToggle />
          <div className="text-sm text-gray-600 dark:text-gray-400">{user?.username}</div>
          <button
            onClick={logout}
            className="text-sm text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-300"
          >
            Logout
          </button>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        <ConversationSidebar
          conversations={conversations}
          currentConversation={currentConversation}
          onSelect={selectConversation}
          onCreate={createConversation}
          onDelete={deleteConversation}
          onRename={updateConversationTitle}
        />

        <div className="flex-1 flex flex-col bg-white dark:bg-gray-900">
          {!currentConversation ? (
            <div className="flex-1 flex items-center justify-center text-gray-400 dark:text-gray-500">
              Select a conversation or create a new one
            </div>
          ) : (
            <>
              {error && (
                <div className="bg-red-50 text-red-600 dark:bg-red-950/30 dark:text-red-400 px-4 py-2 text-sm">
                  {error}
                </div>
              )}

              {!isConnected && (
                <div className="bg-yellow-50 text-yellow-600 dark:bg-yellow-950/30 dark:text-yellow-400 px-4 py-2 text-sm">
                  Connecting...
                </div>
              )}

              <MessageList
                messages={messages}
                streamingMessage={streamingMessage}
                isStreaming={isStreaming}
                toolExecutions={toolExecutions}
                expandedToolId={expandedToolId}
                onToggleExpandTool={setExpandedToolId}
              />
              <MessageInput
                onSend={sendMessage}
                disabled={!isConnected || isStreaming}
              />
            </>
          )}
        </div>
      </div>
    </div>
  );
};
