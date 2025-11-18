// ABOUTME: Expandable tool execution card showing full tool details with accordion behavior
// ABOUTME: Displays tool name, status, source, and collapsible input/result/timing sections

import React from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Loader2, Check, ChevronDown } from "lucide-react";
import type { ToolExecution } from "../../contexts/ChatContext";

interface ToolExecutionCardProps {
  execution: ToolExecution;
  isExpanded: boolean;
  onToggleExpand: (id: string) => void;
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({
  execution,
  isExpanded,
  onToggleExpand,
}) => {
  const isMcpTool = execution.source === "mcp";

  const handleToggle = () => {
    onToggleExpand(execution.id);
  };

  const formatJSON = (content: string): string => {
    try {
      const parsed = JSON.parse(content);
      return JSON.stringify(parsed, null, 2);
    } catch {
      return content;
    }
  };

  const calculateDuration = (startTime: string, endTime: string): string => {
    const start = new Date(startTime).getTime();
    const end = new Date(endTime).getTime();
    const ms = end - start;
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(2)}s`;
  };

  return (
    <Card
      className={`my-1.5 border-l-4 cursor-pointer transition-all ${
        isMcpTool
          ? "border-l-purple-500 bg-purple-50/50 dark:border-l-purple-400 dark:bg-purple-950/30"
          : "border-l-blue-500 bg-blue-50/50 dark:border-l-blue-400 dark:bg-blue-950/30"
      }`}
    >
      {/* Header: Always visible, clickable */}
      <div
        className="px-4 py-3 flex items-center gap-3 hover:opacity-80"
        onClick={handleToggle}
      >
        {/* Status icon */}
        <div className="flex-shrink-0">
          {execution.status === "running" && (
            <Loader2 className="h-4 w-4 animate-spin text-blue-600 dark:text-blue-400" />
          )}
          {execution.status === "completed" && (
            <Check className="h-4 w-4 text-green-600 dark:text-green-400" />
          )}
        </div>

        {/* Tool name badge */}
        <Badge
          variant="outline"
          className={`font-mono text-xs ${
            isMcpTool
              ? "border-purple-300 dark:border-purple-600"
              : "border-blue-300 dark:border-blue-600"
          }`}
        >
          {execution.toolName}
        </Badge>

        {/* Source badge */}
        {isMcpTool && (
          <Badge className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-300">
            MCP
          </Badge>
        )}

        {/* Quick preview if completed and collapsed */}
        {execution.toolResult && !isExpanded && (
          <span className="text-xs text-gray-600 dark:text-gray-400 font-mono truncate max-w-md">
            → {execution.toolResult}
          </span>
        )}

        {/* Chevron indicator */}
        <ChevronDown
          className={`ml-auto h-4 w-4 transition-transform text-gray-500 dark:text-gray-400 ${
            isExpanded ? "rotate-180" : ""
          }`}
        />
      </div>

      {/* Body: Expandable sections */}
      {isExpanded && (
        <div className="px-4 py-3 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* Input section */}
          {execution.toolInput && (
            <div>
              <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Arguments
              </div>
              <div className="bg-gray-50 dark:bg-gray-950 rounded border border-gray-200 dark:border-gray-800 overflow-hidden">
                <pre className="text-xs font-mono text-gray-800 dark:text-gray-200 p-3 overflow-x-auto whitespace-pre-wrap break-words">
                  {formatJSON(execution.toolInput)}
                </pre>
              </div>
            </div>
          )}

          {/* Result section */}
          {execution.toolResult && (
            <div>
              <div className="text-xs font-semibold text-gray-700 dark:text-gray-300 mb-1">
                Result
              </div>
              <div
                className="bg-gray-50 dark:bg-gray-950 rounded border border-gray-200 dark:border-gray-800 overflow-y-auto"
                style={{ maxHeight: "500px" }}
              >
                <pre className="text-xs font-mono text-gray-800 dark:text-gray-200 p-3 overflow-x-auto whitespace-pre-wrap break-words">
                  {formatJSON(execution.toolResult)}
                </pre>
              </div>
            </div>
          )}

          {/* Timing section */}
          {execution.endTime && (
            <div className="text-xs text-gray-600 dark:text-gray-400 flex gap-4">
              <div>
                Started: {new Date(execution.startTime).toLocaleTimeString()}
              </div>
              <div>
                Duration: {calculateDuration(execution.startTime, execution.endTime)}
              </div>
            </div>
          )}
        </div>
      )}
    </Card>
  );
};
