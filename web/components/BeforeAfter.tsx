"use client";

import { useState } from "react";

/** Drag to compare: left of the handle is the original photo, right is the redesign. */
export function BeforeAfter({ before, after, alt }: { before: string; after: string; alt: string }) {
  const [pos, setPos] = useState(50);
  return (
    <div className="relative aspect-video w-full select-none overflow-hidden rounded-xl bg-line">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={after} alt={`${alt}, after`} className="absolute inset-0 size-full object-cover" />
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={before}
        alt={`${alt}, before`}
        className="absolute inset-0 size-full object-cover"
        style={{ clipPath: `inset(0 ${100 - pos}% 0 0)` }}
      />
      <div className="pointer-events-none absolute inset-y-0 w-0.5 bg-white shadow" style={{ left: `${pos}%` }}>
        <div className="absolute top-1/2 left-1/2 grid size-8 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white text-xs shadow">
          ⇆
        </div>
      </div>
      <span className="absolute top-2 left-2 rounded bg-black/55 px-1.5 py-0.5 text-[11px] text-white">Before</span>
      <span className="absolute top-2 right-2 rounded bg-black/55 px-1.5 py-0.5 text-[11px] text-white">After</span>
      <input
        type="range"
        min={0}
        max={100}
        value={pos}
        onChange={(e) => setPos(Number(e.target.value))}
        aria-label="Compare before and after"
        className="absolute inset-0 size-full cursor-ew-resize opacity-0"
      />
    </div>
  );
}
