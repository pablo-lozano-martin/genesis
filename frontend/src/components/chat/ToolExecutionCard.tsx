// ABOUTME: Component displaying tool execution with name, input, status, and result
// ABOUTME: Shows completed tool calls inline with chat messages for transparency

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { ToolExecution } from "../../contexts/ChatContext";

interface ToolExecutionCardProps {
  execution: ToolExecution;
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ execution }) => {
  return (
    <Card className="my-2 border-l-4 border-l-blue-500 bg-blue-50">
      <CardContent className="p-3">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="font-mono text-xs">
              {execution.toolName}
            </Badge>
            {execution.status === "running" && (
              <Badge variant="secondary" className="text-xs">
                Running...
              </Badge>
            )}
            {execution.status === "completed" && (
              <Badge variant="default" className="text-xs bg-green-600">
                Completed
              </Badge>
            )}
          </div>
        </div>

        {execution.toolResult && (
          <div className="mt-2 text-sm">
            <span className="font-semibold">Result:</span>{" "}
            <span className="font-mono">{execution.toolResult}</span>
          </div>
        )}
      </CardContent>
    </Card>
  );
};
