"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useRef, useState } from "react";
import { HowItWorks } from "@/components/HowItWorks";
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
    <div className="isolate flex min-h-dvh flex-col pt-8 lg:pt-12">
      {/* the home page sits on beige; isolate keeps it above the white body */}
      <div aria-hidden className="fixed inset-0 -z-10 bg-veil" />
      <Image src="/RoomTake.svg" alt="Roomtake" width={78} height={60} priority />

      {/* Phone: headline, the how-it-works demo, buttons. Desktop: headline and
          buttons on the left, the demo on the right. */}
      <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-x-20 lg:py-16">
        <section className="mt-14 lg:col-start-1 lg:row-start-1 lg:mt-0 lg:self-end">
          <h1 className="text-[42px] font-semibold leading-[1.05] tracking-tight lg:text-[72px] lg:leading-[1]">
            Same room.
            <br />
            Better take.
          </h1>
          <p className="mt-5 max-w-[30ch] text-[17px] leading-relaxed text-muted lg:mt-8 lg:text-xl">
            Your own room, redesigned around how you live in it, with pieces you can actually buy.
          </p>
        </section>

        <section aria-label="How it works" className="mt-10 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0 lg:self-center">
          <HowItWorks />
        </section>

        <div className="mt-auto space-y-3 pt-8 lg:col-start-1 lg:row-start-2 lg:mt-10 lg:max-w-md lg:self-start lg:pt-0">
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
            className="relative w-full overflow-hidden rounded-full bg-ink py-4 hover:bg-[#2c3734] text-base font-medium text-white transition active:scale-[0.99] disabled:opacity-90"
          >
            {progress !== null && (
              <span
                className="absolute inset-y-0 left-0 bg-white/15 transition-all"
                style={{ width: `${progress}%` }}
              />
            )}
            <span className="relative">{progress === null ? "Film your room" : `Uploading… ${progress}%`}</span>
          </button>
          <Link
            href={`/room/${DEMO_ROOM}`}
            className="block w-full rounded-full bg-card py-4 hover:bg-[#fbf9f7] text-center text-base font-medium shadow-[var(--shadow-card)] transition active:scale-[0.99]"
          >
            Try our demo living room
          </Link>
          {error && <p className="text-center text-sm text-warn">{error}</p>}
          <Link href="/curate" className="block pt-3 text-center text-xs text-muted underline-offset-4 hover:underline">
            Product catalog
          </Link>
        </div>
      </div>
    </div>
  );
}
