"use client";

import { useEffect, useRef, useState } from "react";
import { Microphone, Stop } from "@/components/Icons";
import { transcribe } from "@/lib/api";

export type DictationState = "idle" | "recording" | "transcribing";

const MAX_SECONDS = 30; // a change to the room is a sentence or two

/** Tap to talk, tap again to stop; Muse Voice Transcribe turns it into text. */
export function useDictation(onText: (text: string) => void) {
  const [state, setState] = useState<DictationState>("idle");
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const recorder = useRef<MediaRecorder | null>(null);

  useEffect(() => {
    if (state !== "recording") return;
    setSeconds(0);
    const t = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(t);
  }, [state]);

  useEffect(() => {
    if (state === "recording" && seconds >= MAX_SECONDS) recorder.current?.stop();
  }, [state, seconds]);

  async function start() {
    setError(null);
    let stream: MediaStream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Allow the microphone to talk to the stylist.");
      return;
    }
    // Chrome records WebM/Opus, Safari MP4/AAC; the server converts either
    const type = ["audio/webm;codecs=opus", "audio/mp4"].find((t) => MediaRecorder.isTypeSupported(t));
    const rec = new MediaRecorder(stream, type ? { mimeType: type } : undefined);
    const chunks: Blob[] = [];
    rec.ondataavailable = (e) => e.data.size && chunks.push(e.data);
    rec.onstop = async () => {
      stream.getTracks().forEach((t) => t.stop());
      setState("transcribing");
      try {
        const text = await transcribe(new Blob(chunks, { type: rec.mimeType }));
        if (text) onText(text);
        else setError("We didn't catch that. Try again a little closer.");
      } catch {
        setError("Couldn't transcribe that. Try again or type it.");
      }
      setState("idle");
    };
    recorder.current = rec;
    rec.start();
    setState("recording");
  }

  const toggle = () => (state === "recording" ? recorder.current?.stop() : state === "idle" && start());
  return { state, seconds, error, toggle };
}

/** The mic button beside Send: beige at rest, olive with a pulse while listening. */
export function MicButton({
  state,
  disabled,
  onClick,
}: {
  state: DictationState;
  disabled?: boolean;
  onClick: () => void;
}) {
  const recording = state === "recording";
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled || state === "transcribing"}
      aria-label={recording ? "Stop and transcribe" : "Talk to the stylist"}
      aria-pressed={recording}
      className={`relative grid size-11 shrink-0 place-items-center rounded-full text-[20px] transition-[background-color,color,transform] active:scale-95 disabled:opacity-40 ${
        recording ? "bg-olive text-white" : "bg-veil text-olive hover:bg-[#d6cabd]"
      }`}
    >
      {recording && <span aria-hidden className="mic-pulse absolute inset-0 rounded-full" />}
      {recording ? <Stop className="relative text-[16px]" /> : <Microphone />}
    </button>
  );
}
