// ABOUTME: Component displaying tool execution with name, input, status, and result
// ABOUTME: Shows completed tool calls inline with chat messages for transparency

import React from "react";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Check, Loader2 } from "lucide-react";
import type { ToolExecution } from "../../contexts/ChatContext";

interface ToolExecutionCardProps {
  execution: ToolExecution;
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  const isMcpTool = execution.source === "mcp";

  return (
    <Card className={`my-1.5 border-l-2 ${isMcpTool ? "border-l-purple-500 bg-purple-50/50 dark:border-l-purple-900 dark:bg-purple-950/20" : "border-l-blue-500 bg-blue-50/50 dark:border-l-blue-900 dark:bg-blue-950/20"}`}>
      <div className="px-3 py-2">
        <div className="flex items-center gap-2">
          {execution.status === "running" && (
            <Loader2 className="h-3.5 w-3.5 animate-spin text-blue-600 dark:text-blue-400" />
          )}
          {execution.status === "completed" && (
            <Check className="h-3.5 w-3.5 text-green-600 dark:text-green-400" />
          )}
          <Badge variant="outline" className={`font-mono text-xs ${isMcpTool ? "border-purple-300" : ""}`}>
            {execution.toolName}
          </Badge>
          {isMcpTool && (
            <Badge variant="secondary" className="text-xs bg-purple-100 text-purple-700 dark:bg-purple-950/40 dark:text-purple-300">
              MCP
            </Badge>
          )}
          {execution.toolResult && (
            <span className="text-xs text-gray-600 dark:text-gray-400 font-mono">
              → {execution.toolResult}
            </span>
          )}
        </div>
      </div>
    </Card>
  );
};
