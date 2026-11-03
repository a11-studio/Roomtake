"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useRef, useState } from "react";
import { HowItWorks } from "@/components/HowItWorks";
import { Camera, Close, Couch, Plus } from "@/components/Icons";
import { uploadPhotos } from "@/lib/api";

const DEMO_ROOM = "IMG_1184";
const MAX_PHOTOS = 3;

/** Local previews for picked photos, released when they change. */
function usePreviews(files: File[]) {
  const urls = useMemo(() => files.map((f) => URL.createObjectURL(f)), [files]);
  useEffect(() => () => urls.forEach((u) => URL.revokeObjectURL(u)), [urls]);
  return urls;
}

export default function Home() {
  const router = useRouter();
  const input = useRef<HTMLInputElement>(null);
  const [photos, setPhotos] = useState<File[]>([]);
  const previews = usePreviews(photos);
  const [progress, setProgress] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);

  // The camera takes one photo at a time (only the library allows several),
  // so photos collect in a tray: add up to three, then start.
  function onPick(files: FileList | null) {
    if (files?.length) setPhotos((p) => [...p, ...files].slice(0, MAX_PHOTOS));
    if (input.current) input.current.value = ""; // the same photo can be picked again
  }

  async function start() {
    setError(null);
    setProgress(0);
    try {
      const { id } = await uploadPhotos(photos, setProgress);
      router.push(`/room/${id}`);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed");
      setProgress(null);
    }
  }

  return (
    <div className="home flex min-h-dvh flex-col pt-6 lg:pt-12">
      <Image src="/RoomTake.svg" alt="Roomtake" width={78} height={60} priority />

      {/* Phone: headline, the how-it-works demo, buttons. Desktop: headline and
          buttons on the left, the demo on the right. */}
      <div className="flex flex-1 flex-col lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-x-20 lg:py-16">
        <section className="mt-9 lg:col-start-1 lg:row-start-1 lg:mt-0 lg:self-end">
          <h1 className="text-[42px] font-semibold leading-[1.05] tracking-tight lg:text-[72px] lg:leading-[1]">
            Same room.
            <br />
            Better take.
          </h1>
          <p className="mt-3 text-[16px] leading-[1.45] text-balance text-muted lg:mt-8 lg:max-w-[46ch] lg:text-xl lg:leading-relaxed">
            Your own room, redesigned around how you live in it, with pieces you can actually buy.
          </p>
        </section>

        <section aria-label="How it works" className="mt-5 lg:col-start-2 lg:row-span-2 lg:row-start-1 lg:mt-0 lg:self-center">
          <HowItWorks />
        </section>

        <div className="mt-auto space-y-3 pt-6 lg:col-start-1 lg:row-start-2 lg:mt-10 lg:max-w-md lg:self-start lg:pt-0">
          <input
            ref={input}
            type="file"
            accept="image/*"
            multiple
            className="hidden"
            onChange={(e) => onPick(e.target.files)}
          />
          {photos.length > 0 && (
            <div className="pop-in rounded-[28px] bg-card p-4 shadow-[var(--shadow-card)]">
              <ul className="flex gap-2.5">
                {previews.map((url, i) => (
                  <li key={url} className="pop-in relative size-[72px] shrink-0">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={url} alt={`Photo ${i + 1}`} className="size-full rounded-2xl object-cover" />
                    {progress === null && (
                      <button
                        onClick={() => setPhotos(photos.filter((_, j) => j !== i))}
                        aria-label={`Remove photo ${i + 1}`}
                        className="absolute -top-1.5 -right-1.5 grid size-6 place-items-center rounded-full bg-ink text-[11px] text-white ring-2 ring-card"
                      >
                        <Close />
                      </button>
                    )}
                  </li>
                ))}
                {photos.length < MAX_PHOTOS && progress === null && (
                  <li>
                    <button
                      onClick={() => input.current?.click()}
                      aria-label="Add another photo"
                      className="grid size-[72px] place-items-center rounded-2xl border border-dashed border-[#c9b9a7] text-[20px] text-umber transition-[background-color,transform] hover:bg-[#f7f4f1] active:scale-95"
                    >
                      <Plus />
                    </button>
                  </li>
                )}
              </ul>
              <p className="mt-3 text-[13px] leading-snug text-muted">
                {photos.length < MAX_PHOTOS
                  ? "Add the room from another corner, or your balcony. Up to three photos."
                  : "Three photos, that's plenty."}
              </p>
            </div>
          )}
          <button
            onClick={() => (photos.length ? start() : input.current?.click())}
            disabled={progress !== null}
            className="relative w-full overflow-hidden rounded-full bg-ink py-4 hover:bg-[#2c3734] text-base font-medium text-white transition active:scale-[0.99] disabled:opacity-90"
          >
            {progress !== null && (
              <span
                className="absolute inset-y-0 left-0 bg-white/15 transition-all"
                style={{ width: `${progress}%` }}
              />
            )}
            <span className="relative inline-flex items-center justify-center gap-2">
              {progress === null && photos.length === 0 && <Camera className="text-[19px]" />}
              {progress !== null
                ? `Uploading… ${progress}%`
                : photos.length
                  ? `Design my room · ${photos.length} ${photos.length === 1 ? "photo" : "photos"}`
                  : "Snap your room"}
            </span>
          </button>
          <Link
            href={`/room/${DEMO_ROOM}`}
            className="flex w-full items-center justify-center gap-2 rounded-full bg-card py-4 hover:bg-[#fbf9f7] text-base font-medium shadow-[var(--shadow-card)] transition active:scale-[0.99]"
          >
            <Couch className="text-[19px]" />
            Try our demo living room
          </Link>
          {error && <p className="text-center text-sm text-warn">{error}</p>}
          {/* the catalog editor is local only (app/curate/layout.tsx) */}
          {process.env.NODE_ENV === "development" && (
            <Link href="/curate" className="block pt-3 text-center text-xs text-muted underline-offset-4 hover:underline">
              Product catalog
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}
