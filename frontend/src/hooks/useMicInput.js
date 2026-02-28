import { useState, useRef, useCallback } from 'react';

/**
 * Provides microphone recording via MediaRecorder.
 * Returns raw audio chunks as a Blob and a text transcript
 * (using the Web Speech API when available, falling back to
 * returning just the blob for server-side STT).
 */
export default function useMicInput({ onTranscript } = {}) {
  const [isRecording, setIsRecording] = useState(false);
  const [error, setError] = useState(null);
  const mediaRecorderRef = useRef(null);
  const chunksRef = useRef([]);
  const recognitionRef = useRef(null);

  const start = useCallback(async () => {
    try {
      setError(null);
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const recorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' });
      chunksRef.current = [];

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        stream.getTracks().forEach(t => t.stop());
      };

      mediaRecorderRef.current = recorder;
      recorder.start(250); // chunk every 250ms
      setIsRecording(true);

      // Optional: start Web Speech API for live transcript
      if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
        const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
        const recognition = new SpeechRecognition();
        recognition.continuous = true;
        recognition.interimResults = false;
        recognition.lang = 'en-US';
        recognition.onresult = (event) => {
          const last = event.results[event.results.length - 1];
          if (last.isFinal && onTranscript) {
            onTranscript(last[0].transcript);
          }
        };
        recognition.onerror = () => {}; // silent
        recognition.start();
        recognitionRef.current = recognition;
      }
    } catch (err) {
      setError('Microphone access denied');
      console.error('Mic error:', err);
    }
  }, [onTranscript]);

  const stop = useCallback(() => {
    return new Promise((resolve) => {
      const recorder = mediaRecorderRef.current;
      if (recorder && recorder.state !== 'inactive') {
        recorder.onstop = () => {
          recorder.stream?.getTracks().forEach(t => t.stop());
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' });
          resolve(blob);
        };
        recorder.stop();
      } else {
        resolve(null);
      }
      setIsRecording(false);

      if (recognitionRef.current) {
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
    });
  }, []);

  const cancel = useCallback(() => {
    const recorder = mediaRecorderRef.current;
    if (recorder && recorder.state !== 'inactive') {
      recorder.stop();
      recorder.stream?.getTracks().forEach(t => t.stop());
    }
    setIsRecording(false);
    chunksRef.current = [];

    if (recognitionRef.current) {
      recognitionRef.current.stop();
      recognitionRef.current = null;
    }
  }, []);

  return { isRecording, error, start, stop, cancel };
}
