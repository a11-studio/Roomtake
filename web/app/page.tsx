"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { uploadVideo } from "@/lib/api";

const DEMO_ROOM = "IMG_1184";

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
    <div className="flex min-h-dvh flex-col pt-10">
      <Image src="/RoomTake.svg" alt="Roomtake" width={93} height={72} priority />

      <section className="mt-12">
        <h1 className="text-4xl font-semibold leading-tight tracking-tight">
          Same room.
          <br />
          Better take.
        </h1>
        <p className="mt-4 text-base text-muted">
          Film your room for 30 seconds. We find what&apos;s in it, suggest a few real products
          that fit, and show them in your own photo. Everything else stays as it is.
        </p>
      </section>

      <ol className="mt-8 space-y-3 text-sm">
        {["Walk slowly around the room with your phone", "We map every piece of furniture", "Get a redesign with products you can buy"].map(
          (step, i) => (
            <li key={step} className="flex items-center gap-3">
              <span className="grid size-7 shrink-0 place-items-center rounded-full bg-brand text-xs font-semibold">
                {i + 1}
              </span>
              {step}
            </li>
          ),
        )}
      </ol>

      <div className="mt-auto space-y-3 pt-10">
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
          className="w-full rounded-2xl bg-ink py-4 text-base font-medium text-white disabled:opacity-70"
        >
          {progress === null ? "Film or upload your room" : `Uploading… ${progress}%`}
        </button>
        <Link
          href={`/room/${DEMO_ROOM}`}
          className="block w-full rounded-2xl border border-line bg-card py-4 text-center text-base font-medium"
        >
          Try our demo living room
        </Link>
        {error && <p className="text-sm text-warn">{error}</p>}
        <Link href="/curate" className="block pt-2 text-center text-xs text-muted underline-offset-2 hover:underline">
          Product catalog
        </Link>
      </div>
    </div>
  );
}
