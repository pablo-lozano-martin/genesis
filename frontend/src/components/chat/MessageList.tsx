// ABOUTME: Message list component for displaying chat messages
// ABOUTME: Shows user and assistant messages with auto-scroll

import React, { useEffect, useRef } from "react";
import { Message } from "../../services/conversationService";

interface MessageListProps {
  messages: Message[];
  streamingMessage: string | null;
}

export const MessageList: React.FC<MessageListProps> = ({ messages, streamingMessage }) => {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streamingMessage]);

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && !streamingMessage && (
        <div className="flex items-center justify-center h-full text-gray-400">
          Start a conversation
        </div>
      )}

      {messages.map((message) => (
        <div
          key={message.id}
          className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
        >
          <div
            className={`max-w-[70%] rounded-lg px-4 py-2 ${
              message.role === "user"
                ? "bg-blue-500 text-white"
                : "bg-gray-100 text-gray-900"
            }`}
          >
            <div className="whitespace-pre-wrap break-words">{message.content}</div>
          </div>
        </div>
      ))}

      {streamingMessage && (
        <div className="flex justify-start">
          <div className="max-w-[70%] rounded-lg px-4 py-2 bg-gray-100 text-gray-900">
            <div className="whitespace-pre-wrap break-words">{streamingMessage}</div>
            <div className="mt-1 text-xs text-gray-400">●</div>
          </div>
        </div>
      )}

      <div ref={bottomRef} />
    </div>
  );
};
