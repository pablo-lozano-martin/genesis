// ABOUTME: Message input component for sending chat messages
// ABOUTME: Textarea with microphone button for speech-to-text and send button

import React, { useState } from "react";
import type { KeyboardEvent } from "react";
import { Mic, Loader2 } from "lucide-react";
import { useSpeechToText } from "../../hooks/useSpeechToText";

interface MessageInputProps {
  onSend: (content: string) => void;
  disabled?: boolean;
}

export const MessageInput: React.FC<MessageInputProps> = ({ onSend, disabled }) => {
  const [input, setInput] = useState("");

  const {
    isRecording,
    isTranscribing,
    error: transcriptionError,
    startRecording,
    stopRecording
  } = useSpeechToText({
    onTranscriptComplete: (text) => {
      setInput(text);
    }
  });

  const handleSend = () => {
    if (!input.trim() || disabled) return;
    onSend(input.trim());
    setInput("");
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="border-t dark:border-gray-700 p-4">
      <div className="flex gap-2">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={disabled}
          className="flex-1 resize-none rounded-lg border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-white dark:placeholder-gray-500 px-4 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-800 disabled:cursor-not-allowed"
          rows={1}
        />
        <button
          onClick={isRecording ? stopRecording : startRecording}
          disabled={disabled || isTranscribing}
          aria-label={isRecording ? "Stop recording" : "Start recording"}
          aria-pressed={isRecording}
          className={`px-4 py-2 rounded-lg border transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed ${
            isRecording
              ? "bg-red-50 border-red-500 text-red-600 hover:bg-red-100 dark:bg-red-950/30 dark:border-red-800 dark:text-red-400 dark:hover:bg-red-950/50 animate-pulse"
              : "bg-white border-gray-300 text-gray-700 hover:bg-gray-50 dark:bg-gray-800 dark:border-gray-600 dark:text-gray-300 dark:hover:bg-gray-700"
          }`}
        >
          {isTranscribing ? (
            <Loader2 className="h-5 w-5 animate-spin" />
          ) : (
            <Mic className="h-5 w-5" />
          )}
        </button>
        <button
          onClick={handleSend}
          disabled={!input.trim() || disabled}
          className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
      {transcriptionError && (
        <div className="text-red-500 dark:text-red-400 text-sm mt-2">
          {transcriptionError}
        </div>
      )}
    </div>
  );
};
