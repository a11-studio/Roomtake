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
      <header className="flex items-center justify-between pt-5">
        <Link href="/">
          <Image src="/RoomTake.svg" alt="Roomtake" width={46} height={36} />
        </Link>
        {stage === "look" && (
          <button onClick={() => setStage("prefs")} className="text-sm text-muted underline-offset-2 hover:underline">
            New style
          </button>
        )}
      </header>

      {stage === "loading" && <p className="pt-10 text-sm text-muted">Loading…</p>}
      {stage === "analyzing" && <Analysis roomId={id} onDone={load} />}
      {stage === "prefs" && room && <Preferences roomId={id} room={room} busy={busy} onSubmit={onStyle} />}
      {stage === "look" && lookId && <LookView key={lookId} roomId={id} lookId={lookId} busy={busy} onRevise={onRevise} />}
      {error && <p className="mt-6 text-sm text-warn">{error}</p>}
    </>
  );
}
