"use client";

import { useMemo, useState } from "react";
import { fileUrl, type Preferences as Prefs, type Room } from "@/lib/api";

const STYLES = ["Scandinavian", "Modern", "Japandi", "Boho", "Industrial"];

/** Room summary + the three quick choices before the architect runs. */
export function Preferences({
  roomId,
  room,
  busy,
  onSubmit,
}: {
  roomId: string;
  room: Room;
  busy: boolean;
  onSubmit: (p: Prefs) => void;
}) {
  const [style, setStyle] = useState<string | undefined>();
  const [budget, setBudget] = useState(2000);
  const [keep, setKeep] = useState<string[]>([]);

  const counts = useMemo(() => {
    const c = new Map<string, number>();
    room.objects.filter((o) => o.category !== "zone").forEach((o) => c.set(o.label, (c.get(o.label) ?? 0) + 1));
    return [...c.entries()];
  }, [room]);
  const furniture = room.objects.filter((o) => o.category === "furniture");
  const freeSpace = room.objects.some((o) => o.category === "zone" && o.label !== "floor");

  return (
    <div className="pt-6">
      <div className="-mx-4 flex snap-x gap-2 overflow-x-auto px-4 pb-2">
        {room.keyframes.map((k) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={k.file}
            src={fileUrl(roomId, k.file)}
            alt=""
            className="aspect-video w-56 shrink-0 snap-start rounded-xl object-cover"
          />
        ))}
      </div>

      <h1 className="mt-5 text-2xl font-semibold">We found {room.objects.length} things</h1>
      <p className="mt-1 text-sm text-muted">
        {counts.map(([label, n]) => (n > 1 ? `${n} ${label}s` : label)).join(", ")}
        {freeSpace && ". Plus free space on the balcony, ready for something new."}
      </p>

      <section className="mt-8">
        <h2 className="text-sm font-medium">Style</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {STYLES.map((s) => (
            <button
              key={s}
              onClick={() => setStyle(style === s ? undefined : s)}
              className={`rounded-full px-3 py-1.5 text-sm ring-1 ${style === s ? "bg-brand ring-brand-strong" : "bg-card ring-line"}`}
            >
              {s}
            </button>
          ))}
        </div>
      </section>

      <section className="mt-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-sm font-medium">Budget to shop the look</h2>
          <span className="text-sm tabular-nums">€{budget.toLocaleString("en-IE")}</span>
        </div>
        <input
          type="range"
          min={100}
          max={8000}
          step={100}
          value={budget}
          onChange={(e) => setBudget(Number(e.target.value))}
          className="mt-2 w-full accent-[var(--brand-strong)]"
        />
      </section>

      <section className="mt-6">
        <h2 className="text-sm font-medium">Keep as it is</h2>
        <div className="mt-2 flex flex-wrap gap-2">
          {furniture.map((o) => {
            const on = keep.includes(o.id);
            return (
              <button
                key={o.id}
                onClick={() => setKeep(on ? keep.filter((k) => k !== o.id) : [...keep, o.id])}
                className={`rounded-full px-3 py-1.5 text-sm ring-1 ${on ? "bg-ink text-white ring-ink" : "bg-card ring-line"}`}
              >
                {o.color.name} {o.label}
              </button>
            );
          })}
        </div>
      </section>

      <button
        onClick={() => onSubmit({ style, budget, keep })}
        disabled={busy}
        className="mt-10 w-full rounded-2xl bg-ink py-4 text-base font-medium text-white disabled:opacity-70"
      >
        {busy ? "Starting…" : style ? `Show my room in ${style}` : "Surprise me with a style"}
      </button>
      <p className="mt-2 text-center text-xs text-muted">Same room, same layout, new look · about a minute</p>
    </div>
  );
}
