"use client";

import React, { useState, useRef, useEffect } from "react";
import { Locale } from "@/lib/i18n";
import { MicIcon, MicOffIcon, Volume2Icon } from "./icons";
import { API_BASE_URL } from "@/lib/api";

interface VoiceRecorderProps {
  locale: Locale;
  onTranscription: (text: string) => void;
  disabled?: boolean;
}

// Preload browser speech voices
let cachedVoices: SpeechSynthesisVoice[] = [];
if (typeof window !== "undefined" && "speechSynthesis" in window) {
  cachedVoices = window.speechSynthesis.getVoices();
  window.speechSynthesis.onvoiceschanged = () => {
    cachedVoices = window.speechSynthesis.getVoices();
  };
}

export function playSpokenResponse(text: string, lang: string = "en") {
  if (typeof window === "undefined" || !("speechSynthesis" in window)) return;

  // Cancel any ongoing speech
  window.speechSynthesis.cancel();

  // Strip markdown formatting and bracketed citations for natural speech
  const cleanText = text
    .replace(/\[PMK-[^\]]+\]/g, "")
    .replace(/[*_#`]/g, "")
    .replace(/\n+/g, ". ")
    .trim();

  if (!cleanText) return;

  const langToVoiceTag: Record<string, string> = {
    hi: "hi-IN",
    pa: "pa-IN",
    mr: "mr-IN",
    te: "te-IN",
    ta: "ta-IN",
    bn: "bn-IN",
    gu: "gu-IN",
    kn: "kn-IN",
    en: "en-IN",
  };

  const langNames: Record<string, string> = {
    hi: "hindi",
    pa: "punjabi",
    mr: "marathi",
    te: "telugu",
    ta: "tamil",
    bn: "bengali",
    gu: "gujarati",
    kn: "kannada",
    en: "english",
  };

  const targetTag = langToVoiceTag[lang] || "en-IN";
  const utterance = new SpeechSynthesisUtterance(cleanText);
  utterance.lang = targetTag;
  utterance.rate = 1.0;
  utterance.pitch = 1.0;

  const voices = cachedVoices.length > 0 ? cachedVoices : window.speechSynthesis.getVoices();
  const lCode = lang.toLowerCase();
  const lName = langNames[lCode] || "";

  // 1. Look for precise Indic language voice
  const matchedVoice = voices.find((v) => {
    const vLang = v.lang.toLowerCase().replace("_", "-");
    const vName = v.name.toLowerCase();
    return (
      vLang.startsWith(lCode) ||
      (lName && vName.includes(lName))
    );
  });

  if (matchedVoice) {
    utterance.voice = matchedVoice;
  } else if (lCode === "en") {
    const enVoice = voices.find((v) => v.lang.includes("en-IN") || v.lang.includes("en-GB") || v.lang.includes("en"));
    if (enVoice) utterance.voice = enVoice;
  }

  window.speechSynthesis.speak(utterance);
}

export default function VoiceRecorder({
  locale,
  onTranscription,
  disabled = false,
}: VoiceRecorderProps) {
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [recordingSeconds, setRecordingSeconds] = useState(0);

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (typeof window !== "undefined" && "speechSynthesis" in window) {
      cachedVoices = window.speechSynthesis.getVoices();
    }
  }, []);

  const startRecording = async () => {
    try {
      audioChunksRef.current = [];
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, {
        mimeType: MediaRecorder.isTypeSupported("audio/webm")
          ? "audio/webm"
          : MediaRecorder.isTypeSupported("audio/mp4")
          ? "audio/mp4"
          : "",
      });

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: mediaRecorder.mimeType || "audio/webm",
        });
        await handleUpload(audioBlob);
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current = mediaRecorder;
      mediaRecorder.start(250);
      setIsRecording(true);
      setRecordingSeconds(0);

      timerRef.current = setInterval(() => {
        setRecordingSeconds((prev) => prev + 1);
      }, 1000);
    } catch (err) {
      console.warn("Microphone access failed or denied, using simulated audio:", err);
      // Fallback: send synthetic audio blob so the user can test speech anywhere
      const dummyBlob = new Blob([new Uint8Array(1024)], { type: "audio/webm" });
      await handleUpload(dummyBlob);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
      if (timerRef.current) clearInterval(timerRef.current);
    }
  };

  const handleUpload = async (blob: Blob) => {
    setIsProcessing(true);
    try {
      const formData = new FormData();
      formData.append("file", blob, "voice_input.webm");
      formData.append("lang", locale);

      const resp = await fetch(`${API_BASE_URL}/voice/transcribe`, {
        method: "POST",
        body: formData,
      });

      if (resp.ok) {
        const data = await resp.json();
        if (data.text) {
          onTranscription(data.text);
        }
      }
    } catch (e) {
      console.error("Transcription error:", e);
    } finally {
      setIsProcessing(false);
      setRecordingSeconds(0);
    }
  };

  return (
    <div className="inline-flex items-center gap-2">
      {isRecording ? (
        <button
          type="button"
          onClick={stopRecording}
          className="flex items-center gap-2 px-3.5 py-1.5 bg-rose-600 hover:bg-rose-700 text-white rounded-xl text-xs font-bold animate-pulse shadow-sm shadow-rose-900/20"
          title="Click to Stop Recording"
        >
          <span className="w-2.5 h-2.5 rounded-full bg-white animate-ping" />
          <MicOffIcon className="w-4 h-4 text-white" />
          <span>
            {locale === "hi" ? "रिकॉर्डिंग..." : "Recording..."} {recordingSeconds}s
          </span>
          <span className="text-[10px] bg-rose-800 px-1.5 py-0.5 rounded uppercase font-mono">STOP</span>
        </button>
      ) : isProcessing ? (
        <div className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 text-emerald-800 rounded-xl text-xs font-bold border border-emerald-300">
          <div className="w-3.5 h-3.5 border-2 border-emerald-600 border-t-transparent rounded-full animate-spin" />
          <span>{locale === "hi" ? "ट्रांसक्राइब..." : "Transcribing..."}</span>
        </div>
      ) : (
        <button
          type="button"
          onClick={startRecording}
          disabled={disabled}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-emerald-50 hover:bg-emerald-100 text-emerald-800 hover:text-emerald-950 rounded-xl text-xs font-bold border border-emerald-300/80 transition shadow-xs disabled:opacity-50"
          title={locale === "hi" ? "आवाज से बोलें (Voice Input)" : "Speak via Voice (Gemini STT)"}
        >
          <MicIcon className="w-3.5 h-3.5 text-emerald-700" />
          <span>{locale === "hi" ? "बोलें" : "Voice"}</span>
        </button>
      )}
    </div>
  );
}
