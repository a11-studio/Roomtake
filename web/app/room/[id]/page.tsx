"use client";

import Image from "next/image";
import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { Analysis } from "@/components/Analysis";
import { LookView } from "@/components/LookView";
import { Preferences } from "@/components/Preferences";
import { createLook, getRoom, listLooks, reviseLook, type Preferences as Prefs, type Room } from "@/lib/api";

type Stage = "loading" | "analyzing" | "prefs" | "look" | "error";

export default function RoomPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [stage, setStage] = useState<Stage>("loading");
  const [room, setRoom] = useState<Room | null>(null);
  const [lookId, setLookId] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await getRoom(id);
      if (r.status === "processing") return setStage("analyzing");
      if (r.status !== "done" || !r.room) throw new Error(r.error ?? "This room could not be analyzed");
      setRoom(r.room);
      const latest = (await listLooks(id)).find((l) => l.status !== "error");
      setLookId(latest?.id ?? null);
      setStage(latest ? "look" : "prefs");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStage("error");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function run(fn: () => Promise<void>) {
    setBusy(true);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const onStyle = (prefs: Prefs) =>
    run(async () => {
      setLookId((await createLook(id, prefs)).id);
      setStage("look");
    });
  const onRevise = (instruction: string) =>
    run(async () => {
      if (lookId) setLookId((await reviseLook(id, lookId, instruction)).id);
      window.scrollTo({ top: 0, behavior: "smooth" });
    });

  return (
    <>
      <header className="flex items-center justify-between pt-6">
        <Link href="/" aria-label="Home">
          <Image src="/RoomTake-light.svg" alt="Roomtake" width={52} height={40} />
        </Link>
        {stage === "look" && (
          <button
            onClick={() => {
              setStage("prefs");
              window.scrollTo({ top: 0 });
            }}
            className="rounded-full bg-veil px-3.5 py-2 text-sm transition active:scale-95"
          >
            New style
          </button>
        )}
      </header>

      {stage === "loading" && (
        <div className="pt-10">
          <span className="shimmer block aspect-[4/3] w-60 rounded-2xl bg-veil" />
          <span className="shimmer mt-8 block h-8 w-56 rounded-full bg-veil" />
          <span className="shimmer mt-3 block h-4 w-full rounded-full bg-veil" />
        </div>
      )}
      {stage === "analyzing" && <Analysis roomId={id} onDone={load} />}
      {stage === "prefs" && room && <Preferences roomId={id} room={room} busy={busy} onSubmit={onStyle} />}
      {stage === "look" && lookId && <LookView key={lookId} roomId={id} lookId={lookId} busy={busy} onRevise={onRevise} />}
      {error && <p className="mt-8 rounded-2xl bg-card p-4 text-sm text-warn shadow-[var(--shadow-card)]">{error}</p>}
    </>
  );
}
