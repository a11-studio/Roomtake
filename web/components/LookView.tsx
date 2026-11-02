"use client";

import { useEffect, useState } from "react";
import { BeforeAfter } from "@/components/BeforeAfter";
import { fileUrl, getLook, thumb, type Look, type ProductUse } from "@/lib/api";

const QUICK = ["Warmer and cosier", "Keep my sofa", "More plants", "Try Art Deco instead"];

const STAGES: Record<Look["status"], string> = {
  brief: "The stylist is looking at your room…",
  rendering: "Restyling your room with real products, keeping your layout…",
  checking: "Checking your layout is kept…",
  done: "",
  error: "",
};

const money = (n: number | undefined) => (n ?? 0).toLocaleString("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

/** Polls a look until it is done; shows views as soon as each is ready. */
function useLook(roomId: string, lookId: string) {
  const [look, setLook] = useState<Look | null>(null);
  useEffect(() => {
    let alive = true;
    let timer: ReturnType<typeof setTimeout>;
    const tick = async () => {
      try {
        const l = await getLook(roomId, lookId);
        if (!alive) return;
        setLook(l);
        if (l.status !== "done" && l.status !== "error") timer = setTimeout(tick, 1500);
      } catch {
        if (alive) timer = setTimeout(tick, 3000);
      }
    };
    tick();
    return () => {
      alive = false;
      clearTimeout(timer);
    };
  }, [roomId, lookId]);
  return look;
}

function UsedProduct({ use }: { use: ProductUse }) {
  const p = use.product;
  const where = use.for === "add" ? "Added" : `Your new ${use.for}`;
  return (
    <li className="pop-in flex items-center gap-3 rounded-2xl bg-card p-3 ring-1 ring-line">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={thumb(p.image_url)} alt="" className="size-16 shrink-0 rounded-xl bg-paper object-contain" />
      <div className="min-w-0 flex-1">
        <p className="text-[11px] uppercase tracking-wide text-muted">
          {where}
          {use.view !== "main" && ` · ${use.view.replace(" floor", "")}`}
        </p>
        <p className="truncate text-sm font-medium">{p.name_en ?? p.name}</p>
        <p className="text-xs text-muted">
          {money(p.price_eur ?? p.price)}
          {p.width_cm ? ` · ${p.width_cm} cm wide` : ""}
        </p>
      </div>
      <a
        href={p.product_url}
        target="_blank"
        rel="noreferrer"
        className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs font-medium text-white"
      >
        Buy
      </a>
    </li>
  );
}

export function LookView({
  roomId,
  lookId,
  busy,
  onRevise,
}: {
  roomId: string;
  lookId: string;
  busy: boolean;
  onRevise: (instruction: string) => void;
}) {
  const look = useLook(roomId, lookId);
  const [text, setText] = useState("");

  if (!look) return <p className="pt-10 text-sm text-muted">Loading…</p>;
  const working = look.status !== "done" && look.status !== "error";

  return (
    <div className="pt-6">
      {look.brief ? (
        <>
          <p className="text-sm text-muted">{look.instruction ? `“${look.instruction}”` : "Your room, restyled"}</p>
          <h1 className="mt-1 text-2xl font-semibold">{look.brief.title}</h1>
          <p className="mt-2 text-[15px] text-muted">{look.brief.why ?? look.brief.summary}</p>
          {look.brief.palette && (
            <ul className="mt-3 flex flex-wrap gap-1.5">
              {[...new Set([...look.brief.palette, ...(look.brief.materials ?? [])])].map((p) => (
                <li key={p} className="rounded-full bg-card px-2.5 py-1 text-xs ring-1 ring-line">
                  {p}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : (
        <h1 className="text-2xl font-semibold">Designing your look</h1>
      )}

      {working && (
        <p className="mt-5 flex items-center gap-2 text-sm">
          <span className="size-2 animate-pulse rounded-full bg-brand-strong" />
          {STAGES[look.status]}
        </p>
      )}
      {look.status === "error" && <p className="mt-5 text-sm text-warn">{look.error}</p>}

      <div className="mt-6 space-y-4">
        {look.views.map((v, i) => (
          <figure key={v.file} className="overflow-hidden rounded-2xl bg-card ring-1 ring-line">
            {v.current ? (
              <BeforeAfter before={fileUrl(roomId, v.file)} after={fileUrl(roomId, v.current)} alt={v.label} />
            ) : (
              <div className="relative">
                {/* eslint-disable-next-line @next/next/no-img-element */}
                <img src={fileUrl(roomId, v.file)} alt="" className="aspect-video w-full object-cover" />
                <div className="absolute inset-0 grid place-items-center bg-white/45 text-sm font-medium">
                  {i === 0 ? "Restyling…" : "Furnishing the free space…"}
                </div>
              </div>
            )}
            <figcaption className="px-3 py-2 text-xs text-muted">
              {v.kind === "main" ? "Your room" : `Your ${v.label.replace(" floor", "")}`}
            </figcaption>
          </figure>
        ))}
      </div>

      {look.status === "done" && (
        <section className="mt-8">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Real pieces in your design</h2>
            {look.shop.count > 0 && (
              <span className="text-sm tabular-nums text-muted">{money(look.shop.total)}</span>
            )}
          </div>
          {(look.products ?? []).length > 0 ? (
            <>
              <p className="mt-1 text-sm text-muted">
                These are real Westwing products, drawn into your photo. Everything else is a design idea.
              </p>
              <ul className="mt-3 space-y-3">
                {look.products.map((u) => (
                  <UsedProduct key={u.product.id} use={u} />
                ))}
              </ul>
            </>
          ) : (
            <p className="mt-1 text-sm text-muted">
              Nothing in our catalog fits this look yet, so every piece is a design idea.
            </p>
          )}
        </section>
      )}

      {look.status === "done" && (
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
              placeholder="Tell the stylist what to change"
              className="min-w-0 flex-1 rounded-xl bg-paper px-3 py-2.5 text-sm outline-none ring-1 ring-line focus:ring-brand-strong"
            />
            <button disabled={busy} className="rounded-xl bg-ink px-4 text-sm font-medium text-white disabled:opacity-50">
              Send
            </button>
          </form>
        </section>
      )}
    </div>
  );
}
