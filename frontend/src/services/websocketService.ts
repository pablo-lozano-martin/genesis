// ABOUTME: WebSocket service for real-time chat communication
// ABOUTME: Handles WebSocket connection, message sending, and token streaming reception

export const MessageType = {
  MESSAGE: "message",
  TOKEN: "token",
  COMPLETE: "complete",
  ERROR: "error",
  PING: "ping",
  PONG: "pong",
} as const;

export type MessageType = (typeof MessageType)[keyof typeof MessageType];

export interface ClientMessage {
  type: MessageType;
  conversation_id: string;
  content: string;
}

export interface ServerTokenMessage {
  type: typeof MessageType.TOKEN;
  content: string;
}

export interface ServerCompleteMessage {
  type: typeof MessageType.COMPLETE;
  message_id: string;
  conversation_id: string;
}

export interface ServerErrorMessage {
  type: typeof MessageType.ERROR;
  message: string;
  code?: string;
}

export interface ServerPongMessage {
  type: typeof MessageType.PONG;
}

export type ServerMessage = ServerTokenMessage | ServerCompleteMessage | ServerErrorMessage | ServerPongMessage;

export interface WebSocketConfig {
  url: string;
  token: string;
  onToken?: (token: string) => void;
  onComplete?: (messageId: string, conversationId: string) => void;
  onError?: (error: string, code?: string) => void;
  onConnect?: () => void;
  onDisconnect?: () => void;
}

export class WebSocketService {
  private ws: WebSocket | null = null;
  private config: WebSocketConfig;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private pingInterval: ReturnType<typeof setInterval> | null = null;
  private isManualClose = false;

  constructor(config: WebSocketConfig) {
    this.config = config;
  }

  /**
   * Connect to the WebSocket server.
   */
  connect(): void {
    this.isManualClose = false;
    const wsUrl = `${this.config.url}?token=${this.config.token}`;

    try {
      this.ws = new WebSocket(wsUrl);

      this.ws.onopen = () => {
        console.log("WebSocket connected");
        this.reconnectAttempts = 0;
        this.config.onConnect?.();
        this.startPingInterval();
      };

      this.ws.onmessage = (event) => {
        this.handleMessage(event.data);
      };

      this.ws.onerror = (error) => {
        console.error("WebSocket error:", error);
        this.config.onError?.("Connection error", "CONNECTION_ERROR");
      };

      this.ws.onclose = () => {
        console.log("WebSocket disconnected");
        this.stopPingInterval();
        this.config.onDisconnect?.();

        if (!this.isManualClose && this.reconnectAttempts < this.maxReconnectAttempts) {
          this.attemptReconnect();
        }
      };
    } catch (error) {
      console.error("Failed to create WebSocket:", error);
      this.config.onError?.("Failed to connect", "CONNECTION_FAILED");
    }
  }

  /**
   * Handle incoming WebSocket messages.
   */
  private handleMessage(data: string): void {
    try {
      const message: ServerMessage = JSON.parse(data);

      switch (message.type) {
        case MessageType.TOKEN:
          this.config.onToken?.(message.content);
          break;

        case MessageType.COMPLETE:
          this.config.onComplete?.(message.message_id, message.conversation_id);
          break;

        case MessageType.ERROR:
          this.config.onError?.(message.message, message.code);
          break;

        case MessageType.PONG:
          break;

        default:
          console.warn("Unknown message type:", message);
      }
    } catch (error) {
      console.error("Failed to parse WebSocket message:", error);
    }
  }

  /**
   * Send a message to the server.
   */
  sendMessage(conversationId: string, content: string): void {
    if (!this.ws || this.ws.readyState !== WebSocket.OPEN) {
      console.error("WebSocket is not connected");
      this.config.onError?.("Not connected to server", "NOT_CONNECTED");
      return;
    }

    const message: ClientMessage = {
      type: MessageType.MESSAGE,
      conversation_id: conversationId,
      content,
    };

    try {
      this.ws.send(JSON.stringify(message));
    } catch (error) {
      console.error("Failed to send message:", error);
      this.config.onError?.("Failed to send message", "SEND_FAILED");
    }
  }

  /**
   * Attempt to reconnect to the WebSocket server.
   */
  private attemptReconnect(): void {
    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts})`);

    setTimeout(() => {
      this.connect();
    }, delay);
  }

  /**
   * Start periodic ping to keep connection alive.
   */
  private startPingInterval(): void {
    this.pingInterval = setInterval(() => {
      if (this.ws && this.ws.readyState === WebSocket.OPEN) {
        this.ws.send(JSON.stringify({ type: MessageType.PING }));
      }
    }, 30000);
  }

  /**
   * Stop periodic ping interval.
   */
  private stopPingInterval(): void {
    if (this.pingInterval) {
      clearInterval(this.pingInterval);
      this.pingInterval = null;
    }
  }

  /**
   * Close the WebSocket connection.
   */
  disconnect(): void {
    this.isManualClose = true;
    this.stopPingInterval();

    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  /**
   * Check if WebSocket is connected.
   */
  isConnected(): boolean {
    return this.ws !== null && this.ws.readyState === WebSocket.OPEN;
  }

  /**
   * Get current connection state.
   */
  getReadyState(): number | null {
    return this.ws?.readyState ?? null;
  }
}
