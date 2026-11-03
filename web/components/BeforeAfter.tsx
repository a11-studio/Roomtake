"use client";

import { useEffect, useRef, useState } from "react";
import { ArrowsLeftRight } from "@/components/Icons";

type Phase = "waiting" | "revealing" | "ready";

/**
 * One view of the room, from "being drawn" to "drag to compare", as one object.
 *
 * waiting:   the placeholder (the previous design, or the original photo)
 *            softened, with light running over it
 * revealing: the new design has loaded; the original sharpens over the
 *            placeholder, then the divider travels from the right edge to the
 *            middle, uncovering the new room (the payoff)
 * ready:     drag to compare; the divider follows the finger with no easing
 */
export function BeforeAfter({
  before,
  after,
  placeholder,
  alt,
  waitingLabel = "Restyling…",
}: {
  before: string;
  after: string | null;
  placeholder?: string;
  alt: string;
  waitingLabel?: string;
}) {
  const [phase, setPhase] = useState<Phase>("waiting");
  const [pos, setPos] = useState(100);
  // the frame takes the photo's own shape (landscape or portrait), never a crop of it
  const [ratio, setRatio] = useState<number | null>(null);
  const shown = useRef<string | null>(null);

  // Start the reveal only once the new image is decoded, so it never pops in half-loaded.
  useEffect(() => {
    if (!after || shown.current === after) return;
    let alive = true;
    const img = new Image();
    img.src = after;
    img
      .decode()
      .catch(() => {})
      .then(() => {
        if (!alive) return;
        shown.current = after;
        setPos(100);
        setPhase("revealing");
        // let the original sharpen first, then travel to the middle
        setTimeout(() => alive && setPos(50), 450);
        setTimeout(() => alive && setPhase("ready"), 450 + 1100);
      });
    return () => {
      alive = false;
    };
  }, [after]);

  const loaded = phase !== "waiting";
  const travel = phase === "revealing" ? "1.1s var(--ease-travel)" : "0s";

  return (
    <div
      className="relative w-full select-none overflow-hidden bg-line"
      style={{ aspectRatio: ratio ?? 4 / 3 }}
    >
      {/* the new design, underneath */}
      {after && (
        // eslint-disable-next-line @next/next/no-img-element
        <img src={after} alt={`${alt}, after`} className="absolute inset-0 size-full object-cover" />
      )}

      {/* the original photo, clipped to the left of the divider */}
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img
        src={before}
        alt={`${alt}, before`}
        onLoad={(e) => setRatio(e.currentTarget.naturalWidth / e.currentTarget.naturalHeight)}
        className="absolute inset-0 size-full object-cover"
        style={{
          clipPath: `inset(0 ${100 - pos}% 0 0)`,
          opacity: loaded ? 1 : 0,
          transition: `clip-path ${travel}, opacity 0.45s var(--ease-arrive)`,
        }}
      />

      {/* while drawing: the placeholder, softened, with light running over it */}
      <div
        className={`absolute inset-0 transition-opacity duration-500 ${loaded ? "pointer-events-none opacity-0" : "shimmer"}`}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src={placeholder ?? before} alt="" className="size-full scale-[1.02] object-cover opacity-85 blur-[2px]" />
        <span className="trim absolute bottom-3 left-3 rounded-full bg-card/90 px-3 py-2 text-xs font-medium">
          {waitingLabel}
        </span>
      </div>

      {/* divider and labels arrive with the reveal */}
      <div
        className="pointer-events-none absolute inset-y-0 w-0.5 bg-white/90"
        style={{
          left: `${pos}%`,
          opacity: loaded ? 1 : 0,
          transition: `left ${travel}, opacity 0.3s ease`,
        }}
      >
        <div className="absolute top-1/2 left-1/2 grid size-9 -translate-x-1/2 -translate-y-1/2 place-items-center rounded-full bg-white text-[15px] text-ink shadow-[var(--shadow-float)]">
          <ArrowsLeftRight />
        </div>
      </div>
      <div className={`transition-opacity duration-500 ${phase === "ready" ? "opacity-100" : "opacity-0"}`}>
        <span className="trim absolute top-3 left-3 rounded-full bg-white/85 px-2.5 py-1.5 text-[11px] font-medium text-ink backdrop-blur">
          Before
        </span>
        <span className="trim absolute top-3 right-3 rounded-full bg-olive/80 px-2.5 py-1.5 text-[11px] font-medium text-white backdrop-blur">
          After
        </span>
      </div>

      {loaded && (
        <input
          type="range"
          min={0}
          max={100}
          value={pos}
          onChange={(e) => {
            setPhase("ready");
            setPos(Number(e.target.value));
          }}
          aria-label="Compare before and after"
          className="absolute inset-0 size-full cursor-ew-resize opacity-0"
        />
      )}
    </div>
  );
}
