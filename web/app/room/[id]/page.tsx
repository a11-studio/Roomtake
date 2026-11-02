"use client";

import Image from "next/image";
import Link from "next/link";
import { use, useCallback, useEffect, useState } from "react";
import { Analysis } from "@/components/Analysis";
import { PlanView } from "@/components/PlanView";
import { Preferences } from "@/components/Preferences";
import { getPlan, getRoom, makePlan, revisePlan, type Plan, type Preferences as Prefs, type Room } from "@/lib/api";

type Stage = "loading" | "analyzing" | "prefs" | "plan" | "error";

export default function RoomPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const [stage, setStage] = useState<Stage>("loading");
  const [room, setRoom] = useState<Room | null>(null);
  const [plan, setPlan] = useState<Plan | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await getRoom(id);
      if (r.status === "processing") return setStage("analyzing");
      if (r.status !== "done" || !r.room) throw new Error(r.error ?? "This room could not be analyzed");
      setRoom(r.room);
      const p = await getPlan(id);
      setPlan(p);
      setStage(p ? "plan" : "prefs");
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
      setStage("error");
    }
  }, [id]);

  useEffect(() => {
    load();
  }, [load]);

  async function run<T>(fn: () => Promise<T>) {
    setBusy(true);
    setError(null);
    try {
      return await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }

  const onPlan = (prefs: Prefs) =>
    run(async () => {
      setPlan(await makePlan(id, prefs));
      setStage("plan");
    });
  const onRevise = (instruction: string) => run(async () => setPlan(await revisePlan(id, instruction)));

  return (
    <>
      <header className="flex items-center justify-between pt-5">
        <Link href="/">
          <Image src="/RoomTake.svg" alt="Roomtake" width={46} height={36} />
        </Link>
        {stage === "plan" && (
          <button onClick={() => setStage("prefs")} className="text-sm text-muted underline-offset-2 hover:underline">
            Start over
          </button>
        )}
      </header>

      {stage === "loading" && <p className="pt-10 text-sm text-muted">Loading…</p>}
      {stage === "analyzing" && <Analysis roomId={id} onDone={load} />}
      {stage === "prefs" && room && <Preferences roomId={id} room={room} busy={busy} onSubmit={onPlan} />}
      {stage === "plan" && plan && <PlanView roomId={id} plan={plan} busy={busy} onRevise={onRevise} />}
      {error && <p className="mt-6 text-sm text-warn">{error}</p>}
    </>
  );
}
