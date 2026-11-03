"use client";

import { useEffect, useRef } from "react";

/** The looping AI orb (public/orb.*: centre of the orb video, cropped inside
 * its edge so only the orb shows; the circle mask is this element). */
export function Orb({ className = "size-10", active = false }: { className?: string; active?: boolean }) {
  const ref = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    const v = ref.current;
    if (!v) return;
    const still = window.matchMedia("(prefers-reduced-motion: reduce)");
    const sync = () => (still.matches ? v.pause() : v.play().catch(() => {}));
    // iOS Safari sometimes stops at the end despite `loop`: start it over
    const again = () => {
      if (still.matches) return;
      v.currentTime = 0;
      v.play().catch(() => {});
    };
    sync();
    still.addEventListener("change", sync);
    v.addEventListener("ended", again);
    return () => {
      still.removeEventListener("change", sync);
      v.removeEventListener("ended", again);
    };
  }, []);

  return (
    <span
      aria-hidden
      className={`relative block shrink-0 overflow-hidden rounded-full shadow-[inset_0_0_0_1px_rgb(0_0_0/0.06)] transition-transform duration-500 ${
        active ? "scale-110" : ""
      } ${className}`}
    >
      <video ref={ref} poster="/orb.jpg" autoPlay loop muted playsInline preload="auto" className="size-full object-cover">
        {/* H.264 first: Safari loops it reliably; the VP9 copy is the same size */}
        <source src="/orb.mp4" type="video/mp4" />
        <source src="/orb.webm" type="video/webm" />
      </video>
    </span>
  );
}
