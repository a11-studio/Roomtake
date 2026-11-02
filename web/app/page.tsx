"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { uploadVideo } from "@/lib/api";

const DEMO_ROOM = "IMG_1184";

const STEPS = [
  ["Film", "Walk slowly around your room for 30 seconds."],
  ["Pick a style", "Scandinavian, Japandi, Art Deco and more."],
  ["See it, buy it", "Your room restyled with real pieces you can order."],
];

export default function Home() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function onFile(file: File | undefined) {
    if (!file) return;
    setError(null);
    setProgress(0);
    try {
      const { id } = await uploadVideo(file, setProgress);
      router.push(`/room/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setProgress(null);
    }
  }

  return (
    <div className="isolate flex min-h-dvh flex-col pt-8">
      {/* the brand blue lives on the home page only; isolate keeps it above the white body */}
      <div aria-hidden className="fixed inset-0 -z-10 bg-brand" />
      <Image src="/RoomTake.svg" alt="Roomtake" width={78} height={60} priority />

      <section className="mt-14">
        <h1 className="text-[42px] font-semibold leading-[1.05] tracking-tight">
          Same room.
          <br />
          Better take.
        </h1>
        <p className="mt-5 max-w-[30ch] text-[17px] leading-relaxed text-muted">
          Your own room, redesigned around how you live in it, with pieces you can actually buy.
        </p>
      </section>

      <ol className="mt-12 space-y-5">
        {STEPS.map(([title, text], i) => (
          <li key={title} className="flex gap-4">
            <span className="grid size-8 shrink-0 place-items-center rounded-full bg-card text-sm font-semibold shadow-[var(--shadow-card)]">
              {i + 1}
            </span>
            <div>
              <p className="font-medium">{title}</p>
              <p className="text-sm text-muted">{text}</p>
            </div>
          </li>
        ))}
      </ol>

      <div className="mt-auto space-y-3 pt-14">
        <input
          ref={input}
          type="file"
          accept="video/*"
          capture="environment"
          className="hidden"
          onChange={(e) => onFile(e.target.files?.[0])}
        />
        <button
          onClick={() => input.current?.click()}
          disabled={progress !== null}
          className="relative w-full overflow-hidden rounded-2xl bg-ink py-4 text-base font-medium text-white transition active:scale-[0.99] disabled:opacity-90"
        >
          {progress !== null && (
            <span className="absolute inset-y-0 left-0 bg-white/15 transition-all" style={{ width: `${progress}%` }} />
          )}
          <span className="relative">{progress === null ? "Film your room" : `Uploading… ${progress}%`}</span>
        </button>
        <Link
          href={`/room/${DEMO_ROOM}`}
          className="block w-full rounded-2xl bg-card py-4 text-center text-base font-medium shadow-[var(--shadow-card)] transition active:scale-[0.99]"
        >
          Try our demo living room
        </Link>
        {error && <p className="text-center text-sm text-warn">{error}</p>}
        <Link href="/curate" className="block pt-3 text-center text-xs text-muted underline-offset-4 hover:underline">
          Product catalog
        </Link>
      </div>
    </div>
  );
}
