// ABOUTME: Conversation sidebar for managing chat conversations
// ABOUTME: Minimal list of conversations with create and delete actions

import React from "react";
import type { Conversation } from "../../services/conversationService";

interface ConversationSidebarProps {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  onSelect: (id: string) => void;
  onCreate: () => void;
  onDelete: (id: string) => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  currentConversation,
  onSelect,
  onCreate,
  onDelete,
}) => {
  return (
    <div className="w-64 border-r bg-gray-50 flex flex-col">
      <div className="p-4 border-b">
        <button
          onClick={onCreate}
          className="w-full px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600"
        >
          New Chat
        </button>
      </div>

      <div className="flex-1 overflow-y-auto">
        {conversations.map((conv) => (
          <div
            key={conv.id}
            className={`p-4 border-b cursor-pointer hover:bg-gray-100 ${
              currentConversation?.id === conv.id ? "bg-gray-100" : ""
            }`}
            onClick={() => onSelect(conv.id)}
          >
            <div className="flex items-start justify-between gap-2">
              <div className="flex-1 min-w-0">
                <div className="text-sm font-medium truncate">{conv.title}</div>
                <div className="text-xs text-gray-500 mt-1">
                  {conv.message_count} messages
                </div>
              </div>
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  onDelete(conv.id);
                }}
                className="text-gray-400 hover:text-red-500"
              >
                ×
              </button>
            </div>
          </div>
        ))}

        {conversations.length === 0 && (
          <div className="p-4 text-center text-sm text-gray-400">
            No conversations yet
          </div>
        )}
      </div>
    </div>
  );
};
