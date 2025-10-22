// ABOUTME: Conversation API service for managing conversations
// ABOUTME: Handles CRUD operations for conversations via REST API

import axios from "axios";
import { authService } from "./authService";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export interface Conversation {
  id: string;
  user_id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant" | "system";
  content: string;
  created_at: string;
}

export interface CreateConversationRequest {
  title?: string;
}

export interface UpdateConversationRequest {
  title?: string;
}

export class ConversationService {
  private getAuthHeaders() {
    const token = authService.getToken();
    return {
      Authorization: `Bearer ${token}`,
    };
  }

  async listConversations(skip = 0, limit = 100): Promise<Conversation[]> {
    const response = await axios.get(`${API_URL}/api/conversations`, {
      headers: this.getAuthHeaders(),
      params: { skip, limit },
    });
    return response.data;
  }

  async createConversation(data: CreateConversationRequest = {}): Promise<Conversation> {
    const response = await axios.post(`${API_URL}/api/conversations`, data, {
      headers: this.getAuthHeaders(),
    });
    return response.data;
  }

  async getConversation(id: string): Promise<Conversation> {
    const response = await axios.get(`${API_URL}/api/conversations/${id}`, {
      headers: this.getAuthHeaders(),
    });
    return response.data;
  }

  async deleteConversation(id: string): Promise<void> {
    await axios.delete(`${API_URL}/api/conversations/${id}`, {
      headers: this.getAuthHeaders(),
    });
  }

  async updateConversation(
    id: string,
    data: UpdateConversationRequest
  ): Promise<Conversation> {
    const response = await axios.patch(
      `${API_URL}/api/conversations/${id}`,
      data,
      { headers: this.getAuthHeaders() }
    );
    return response.data;
  }

  async getMessages(conversationId: string, skip = 0, limit = 500): Promise<Message[]> {
    const response = await axios.get(`${API_URL}/api/conversations/${conversationId}/messages`, {
      headers: this.getAuthHeaders(),
      params: { skip, limit },
    });
    return response.data;
  }
}

export const conversationService = new ConversationService();
