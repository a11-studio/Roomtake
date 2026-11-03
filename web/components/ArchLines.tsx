import { useMemo } from "react";

// An archway drawn as a line halftone: rows of broken horizontal dashes that
// thicken into a band around an empty arch. The phone demo stands in the
// opening, so the home page reads like a room seen through a doorway.
// Static and seeded, so server and client draw the same lines. Wide screens
// only: on a phone the demo fills the width, so only the arch's crown would
// show, right behind the copy.

const W = 600; // viewBox; the arch is centred
const H = 660;
const R = 210; // inner radius = half the opening's width
const BAND = 92; // how far the dashes reach out from the opening
const SPRING = BAND + R; // y where the semicircle meets the straight sides
const ROW = 10; // row pitch
const CX = W / 2;

function rng(seed: number) {
  return () => {
    seed = (seed * 16807) % 2147483647;
    return seed / 2147483647;
  };
}

/** Distance outside the opening (negative inside). */
function outside(x: number, y: number) {
  return y < SPRING ? Math.hypot(x - CX, y - SPRING) - R : Math.abs(x - CX) - R;
}

const smooth = (t: number) => (t <= 0 ? 0 : t >= 1 ? 1 : t * t * (3 - 2 * t));

function dashes() {
  const rand = rng(7);
  const out: { x: number; y: number; w: number; o: number }[] = [];
  for (let y = 4; y < H; y += ROW) {
    let x = rand() * 12;
    while (x < W) {
      const w = 6 + rand() * 30;
      const d = outside(x + w / 2, y);
      // empty opening, a soft inner edge, a slightly ragged outer edge
      if (d > 0 && d < BAND - rand() * 14) {
        const o = smooth(d / (BAND * 0.55)) * (0.45 + rand() * 0.55);
        if (o > 0.04) out.push({ x, y, w, o });
      }
      x += w + 2 + rand() * 7;
    }
  }
  return out;
}

export function ArchLines({ className = "" }: { className?: string }) {
  const lines = useMemo(dashes, []);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} aria-hidden className={`arch-lines ${className}`}>
      {lines.map((l, i) => (
        <rect key={i} x={l.x} y={l.y} width={l.w} height={1.8} rx={0.9} opacity={l.o} />
      ))}
    </svg>
  );
}
