"use client";

import { useEffect, useState } from "react";
import { BeforeAfter } from "@/components/BeforeAfter";
import { fileUrl, render, type Change, type Plan } from "@/lib/api";

const QUICK = ["Cheaper", "Keep the side table", "More green", "Brighter in the evening"];

const money = (n: number, cur: string | null) =>
  n.toLocaleString("en-US", { style: "currency", currency: cur ?? "USD", maximumFractionDigits: 0 });

function ChangeCard({ roomId, change, index }: { roomId: string; change: Change; index: number }) {
  const [after, setAfter] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);
  const p = change.product;

  useEffect(() => {
    let alive = true;
    setAfter(null);
    setFailed(false);
    render(roomId, change)
      .then((r) => alive && setAfter(fileUrl(roomId, r.after)))
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [roomId, change]);

  const before = fileUrl(roomId, change.best_frame);
  return (
    <article className="pop-in overflow-hidden rounded-2xl bg-card shadow-sm ring-1 ring-line">
      {after ? (
        <BeforeAfter before={before} after={after} alt={p.name} />
      ) : (
        <div className="relative">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={before} alt="" className="aspect-video w-full object-cover" />
          <div className="absolute inset-0 grid place-items-center bg-white/40 text-sm font-medium backdrop-blur-[1px]">
            {failed ? "Couldn't render this one" : "Placing it in your room…"}
          </div>
        </div>
      )}
      <div className="p-4">
        <p className="text-xs uppercase tracking-wide text-muted">
          {index + 1}. {change.action === "replace" ? `Replace the ${change.target_label}` : `Add to the ${change.target_label}`}
        </p>
        <p className="mt-1.5 text-[15px] leading-snug">{change.why}</p>
        <a href={p.product_url} target="_blank" rel="noreferrer" className="mt-4 flex items-center gap-3">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src={p.image_url} alt="" className="size-14 rounded-lg bg-paper object-contain" />
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium">{p.name}</p>
            <p className="text-xs text-muted">
              {change.fits ? "Fits the space" : "Check the size"}
              {change.max_width_cm ? ` · up to ${change.max_width_cm} cm wide` : ""}
            </p>
          </div>
          <span className="text-sm font-semibold tabular-nums">{money(p.price, p.currency)}</span>
        </a>
      </div>
    </article>
  );
}

export function PlanView({
  roomId,
  plan,
  busy,
  onRevise,
}: {
  roomId: string;
  plan: Plan;
  busy: boolean;
  onRevise: (instruction: string) => void;
}) {
  const [text, setText] = useState("");
  return (
    <div className="pt-6">
      <p className="text-sm text-muted">{plan.style}</p>
      <h1 className="mt-1 text-2xl font-semibold leading-snug">Your redesign</h1>
      <p className="mt-2 text-[15px] text-muted">{plan.summary}</p>

      <div className="mt-6 space-y-5">
        {plan.changes.map((c, i) => (
          <ChangeCard key={`${plan.version}-${c.target_id}-${c.product.id}`} roomId={roomId} change={c} index={i} />
        ))}
      </div>

      <section className="mt-8 rounded-2xl bg-card p-4 ring-1 ring-line">
        <h2 className="text-sm font-medium">Shopping list</h2>
        <ul className="mt-3 space-y-2 text-sm">
          {plan.changes.map((c) => (
            <li key={c.product.id + c.target_id} className="flex justify-between gap-3">
              <a href={c.product.product_url} target="_blank" rel="noreferrer" className="truncate underline-offset-2 hover:underline">
                {c.product.name}
              </a>
              <span className="tabular-nums">{money(c.product.price, c.product.currency)}</span>
            </li>
          ))}
        </ul>
        <div className="mt-3 flex justify-between border-t border-line pt-3 font-semibold">
          <span>Total</span>
          <span className="tabular-nums">{money(plan.total, plan.currency)}</span>
        </div>
        {!plan.within_budget && <p className="mt-2 text-xs text-warn">Over your budget</p>}
      </section>

      <section className="sticky bottom-3 mt-8 rounded-2xl bg-card/95 p-3 shadow-lg ring-1 ring-line backdrop-blur">
        <div className="flex gap-2 overflow-x-auto pb-2">
          {QUICK.map((q) => (
            <button
              key={q}
              disabled={busy}
              onClick={() => onRevise(q)}
              className="shrink-0 rounded-full bg-paper px-3 py-1.5 text-sm ring-1 ring-line disabled:opacity-50"
            >
              {q}
            </button>
          ))}
        </div>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            if (text.trim()) onRevise(text.trim());
            setText("");
          }}
        >
          <input
            value={text}
            onChange={(e) => setText(e.target.value)}
            disabled={busy}
            placeholder={busy ? "Updating your plan…" : "Tell the architect what to change"}
            className="min-w-0 flex-1 rounded-xl bg-paper px-3 py-2.5 text-sm outline-none ring-1 ring-line focus:ring-brand-strong"
          />
          <button disabled={busy} className="rounded-xl bg-ink px-4 text-sm font-medium text-white disabled:opacity-50">
            Send
          </button>
        </form>
      </section>
    </div>
  );
}
