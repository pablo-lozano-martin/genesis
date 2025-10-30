// ABOUTME: API client for backend transcription service
// ABOUTME: Handles audio upload and transcription requests with auth headers

import axiosConfig from './axiosConfig';

export interface TranscriptionResponse {
  text: string;
  language: string;
  duration: number;
}

class TranscriptionService {
  private getAuthHeaders() {
    const token = localStorage.getItem('token');
    return token ? { Authorization: `Bearer ${token}` } : {};
  }

  async transcribe(
    audioBlob: Blob,
    conversationId?: string,
    language?: string
  ): Promise<TranscriptionResponse> {
    const formData = new FormData();
    formData.append('audio_file', audioBlob, 'recording.webm');

    if (conversationId) {
      formData.append('conversation_id', conversationId);
    }

    if (language) {
      formData.append('language', language);
    }

    const response = await axiosConfig.post<TranscriptionResponse>(
      '/api/transcribe',
      formData,
      {
        headers: {
          ...this.getAuthHeaders(),
          'Content-Type': 'multipart/form-data',
        },
      }
    );

    return response.data;
  }
}

export const transcriptionService = new TranscriptionService();
