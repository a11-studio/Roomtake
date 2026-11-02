"use client";

import Image from "next/image";
import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { Analysis } from "@/components/Analysis";
import { Plus } from "@/components/Icons";
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

  // Every new screen (analysis, style picker, a new or revised look) starts at the top.
  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [stage, lookId]);

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
    });

  return (
    <>
      <header className="flex items-center justify-between pt-6">
        <Link href="/" aria-label="Home">
          <Image src="/RoomTake-light.svg" alt="Roomtake" width={52} height={40} />
        </Link>
        {stage === "look" && (
          <button
            onClick={() => setStage("prefs")}
            className="inline-flex h-9 items-center gap-1.5 rounded-full bg-ink pr-4 pl-3 text-sm font-medium text-white transition-[background-color,transform] hover:bg-[#2c3734] active:scale-95"
          >
            <Plus className="text-[15px]" />
            <span className="trim">New style</span>
          </button>
        )}
      </header>

      {/* a new screen keeps the header and crossfades only the body */}
      <div key={stage === "look" ? `look-${lookId}` : stage} className="page-in">
        {stage === "loading" && (
          <div className="pt-10">
            <span className="shimmer block aspect-[4/3] w-60 rounded-2xl bg-veil" />
            <span className="shimmer mt-8 block h-8 w-56 rounded-full bg-veil" />
            <span className="shimmer mt-3 block h-4 w-full rounded-full bg-veil" />
          </div>
        )}
        {stage === "analyzing" && <Analysis roomId={id} onDone={load} />}
        {stage === "prefs" && room && <Preferences roomId={id} room={room} busy={busy} onSubmit={onStyle} />}
        {stage === "look" && lookId && (
          <LookView key={lookId} roomId={id} lookId={lookId} busy={busy} onRevise={onRevise} />
        )}
      </div>
      {error && <p className="mt-8 rounded-2xl bg-card p-4 text-sm text-warn shadow-[var(--shadow-card)]">{error}</p>}
    </>
  );
}
