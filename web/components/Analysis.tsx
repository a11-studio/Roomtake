"use client";

import { useEffect, useState } from "react";
import { API, type ProgressEvent } from "@/lib/api";

const TOTAL_CONCEPTS = 23; // backend/app/pipeline/concepts.py

/** Live "what we found" while SAM tracks the video. Calls onDone when the room is ready. */
export function Analysis({ roomId, onDone }: { roomId: string; onDone: () => void }) {
  const [found, setFound] = useState<{ concept: string; count: number }[]>([]);
  const [checked, setChecked] = useState(0);
  const [stage, setStage] = useState("Preparing your video…");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API}/api/rooms/${roomId}/events`);
    es.onmessage = (msg) => {
      const e = JSON.parse(msg.data) as ProgressEvent;
      if (e.type === "keyframes") setStage("Uploading to SAM 3.1…");
      if (e.type === "uploaded") setStage("Looking for furniture…");
      if (e.type === "found") {
        setChecked((n) => n + 1);
        if (e.count > 0) setFound((f) => [...f, { concept: e.concept, count: e.count }]);
      }
      if (e.type === "done") setStage("Done");
      if (e.type === "status") {
        es.close();
        if (e.status === "done") onDone();
        else setError(e.error ?? "Analysis failed");
      }
    };
    es.onerror = () => {
      es.close();
      onDone(); // stream dropped: the page re-reads the room status
    };
    return () => es.close();
  }, [roomId, onDone]);

  const pct = Math.round((checked / TOTAL_CONCEPTS) * 100);
  return (
    <div className="pt-8">
      <p className="text-sm text-muted">Analyzing your room</p>
      <h1 className="mt-1 text-2xl font-semibold">{stage}</h1>
      <div className="mt-5 h-2 overflow-hidden rounded-full bg-line">
        <div className="h-full rounded-full bg-brand-strong transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
      <p className="mt-2 text-xs text-muted">
        {checked}/{TOTAL_CONCEPTS} kinds of things checked · usually 3–5 minutes
      </p>

      <ul className="mt-8 flex flex-wrap gap-2">
        {found.map((f) => (
          <li key={f.concept} className="pop-in rounded-full bg-card px-3 py-1.5 text-sm shadow-sm ring-1 ring-line">
            {f.concept}
            {f.count > 1 && <span className="ml-1 text-muted">×{f.count}</span>}
          </li>
        ))}
      </ul>
      {error && <p className="mt-6 text-sm text-warn">{error}</p>}
    </div>
  );
}
