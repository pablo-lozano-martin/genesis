// ABOUTME: Component displaying tool execution with name, input, status, and result
// ABOUTME: Shows completed tool calls inline with chat messages for transparency

import React from "react";
import type { ToolExecution } from "../../contexts/ChatContext";

interface ToolExecutionCardProps {
  execution: ToolExecution;
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  return (
    <div className="my-2 border-l-4 border-l-blue-500 bg-blue-50 rounded-lg shadow-sm">
      <div className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="px-2 py-1 border border-gray-300 rounded-md bg-white font-mono text-xs">
              {execution.toolName}
            </span>
            {execution.status === "running" && (
              <span className="px-2 py-1 bg-gray-200 text-gray-700 rounded-md text-xs">
                Running...
              </span>
            )}
            {execution.status === "completed" && (
              <span className="px-2 py-1 bg-green-600 text-white rounded-md text-xs">
                Completed
              </span>
            )}
          </div>
        </div>

        {execution.toolResult && (
          <div className="mt-2 text-sm text-gray-900">
            <span className="font-semibold">Result:</span>{" "}
            <span className="font-mono">{execution.toolResult}</span>
          </div>
        )}
      </div>
    </div>
  );
};
