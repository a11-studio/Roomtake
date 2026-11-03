"use client";

import { useEffect, useState } from "react";
import { Count } from "@/components/Count";
import { API, type ProgressEvent } from "@/lib/api";

const TOTAL_CONCEPTS = 23; // backend/app/pipeline/concepts.py

/** Live "what we found" while SAM looks at the photos. Calls onDone when the room is ready. */
export function Analysis({ roomId, onDone }: { roomId: string; onDone: () => void }) {
  const [found, setFound] = useState<{ concept: string; count: number }[]>([]);
  const [checked, setChecked] = useState(0);
  const [stage, setStage] = useState("Preparing your photos");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const es = new EventSource(`${API}/api/rooms/${roomId}/events`);
    es.onmessage = (msg) => {
      const e = JSON.parse(msg.data) as ProgressEvent;
      if (e.type === "keyframes") setStage("Sending them to SAM 3.1");
      if (e.type === "uploaded") setStage("Finding your furniture");
      if (e.type === "found") {
        setChecked((n) => n + 1);
        if (e.count > 0) setFound((f) => [...f, { concept: e.concept, count: e.count }]);
      }
      if (e.type === "done") setStage("Your room is mapped");
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

  const pct = Math.max(4, Math.round((checked / TOTAL_CONCEPTS) * 100));
  return (
    <div className="pt-10">
      <p className="eyebrow">Analyzing your room</p>
      <h1 key={stage} className="pop-in mt-2 text-[28px] font-semibold tracking-tight">
        <span className="thinking">{stage}</span>
      </h1>

      <div className="mt-8 h-1.5 overflow-hidden rounded-full bg-veil">
        <div
          className="h-full rounded-full bg-ink transition-[width] duration-700"
          style={{ width: `${pct}%`, transitionTimingFunction: "var(--ease-travel)" }}
        />
      </div>
      <p className="mt-3 text-sm text-muted">
        {checked} of {TOTAL_CONCEPTS} kinds of things checked · usually under a minute
      </p>

      <section className="mt-10">
        <p className="eyebrow">Found so far</p>
        {found.length === 0 ? (
          <div className="mt-4 flex gap-2">
            {[72, 96, 60].map((w) => (
              <span key={w} className="shimmer h-9 rounded-full bg-veil" style={{ width: w }} />
            ))}
          </div>
        ) : (
          <ul className="mt-4 flex flex-wrap gap-2">
            {found.map((f) => (
              <li
                key={f.concept}
                className={`pop-in inline-flex h-7 items-center gap-1.5 rounded-full bg-[#f4efe9] pl-3 text-[13px] ${
                  f.count > 1 ? "pr-[5px]" : "pr-3"
                }`}
              >
                <span className="trim">{f.concept}</span>
                {f.count > 1 && <Count n={f.count} />}
              </li>
            ))}
          </ul>
        )}
      </section>
      {error && <p className="mt-8 text-sm text-warn">{error}</p>}
    </div>
  );
}
