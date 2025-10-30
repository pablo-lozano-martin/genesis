// ABOUTME: Custom React hook for browser audio recording and transcription
// ABOUTME: Manages MediaRecorder API, audio state, and transcription service calls

import { useState, useRef, useCallback } from 'react';
import { transcriptionService } from '../services/transcriptionService';

interface UseSpeechToTextOptions {
  onTranscriptComplete?: (transcript: string) => void;
  conversationId?: string;
  language?: string;
}

interface UseSpeechToTextReturn {
  isRecording: boolean;
  isTranscribing: boolean;
  error: string | null;
  transcript: string;
  startRecording: () => Promise<void>;
  stopRecording: () => void;
  resetTranscript: () => void;
}

export function useSpeechToText(
  options: UseSpeechToTextOptions = {}
): UseSpeechToTextReturn {
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [transcript, setTranscript] = useState('');

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  const startRecording = useCallback(async () => {
    try {
      setError(null);

      // Request microphone access
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });

      // Create MediaRecorder
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm;codecs=opus'
      });

      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        // Stop all tracks
        stream.getTracks().forEach(track => track.stop());

        // Create audio blob
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });

        // Transcribe
        setIsTranscribing(true);
        try {
          const result = await transcriptionService.transcribe(
            audioBlob,
            options.conversationId,
            options.language
          );

          setTranscript(result.text);
          setError(null);

          if (options.onTranscriptComplete) {
            options.onTranscriptComplete(result.text);
          }
        } catch (err) {
          const errorMessage = err instanceof Error ? err.message : 'Transcription failed';
          setError(errorMessage);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start();
      mediaRecorderRef.current = mediaRecorder;
      setIsRecording(true);

    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : 'Failed to access microphone';
      setError(errorMessage);
      setIsRecording(false);
    }
  }, [options]);

  const stopRecording = useCallback(() => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  }, [isRecording]);

  const resetTranscript = useCallback(() => {
    setTranscript('');
    setError(null);
  }, []);

  return {
    isRecording,
    isTranscribing,
    error,
    transcript,
    startRecording,
    stopRecording,
    resetTranscript,
  };
}
