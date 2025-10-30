// ABOUTME: API client for backend transcription service
// ABOUTME: Handles audio upload and transcription requests with auth headers

import axios from 'axios';
import { authService } from './authService';

export interface TranscriptionResponse {
  text: string;
  language: string;
  duration: number;
}

class TranscriptionService {
  private getAuthHeaders() {
    const token = authService.getToken();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async transcribe(
    audioBlob: Blob,
    conversationId?: string,
    language?: string
  ): Promise<TranscriptionResponse> {
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');

    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    if (language) {
      formData.append('language', language);
    }

    const response = await axios.post<TranscriptionResponse>(
      `${API_URL}/api/transcribe`,
      formData,
      {
        headers: this.getAuthHeaders(),
      }
    );

    return response.data;
  }
}

export const transcriptionService = new TranscriptionService();
