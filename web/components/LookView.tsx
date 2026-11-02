"use client";

import { useEffect, useState } from "react";
import { BeforeAfter } from "@/components/BeforeAfter";
import { fileUrl, getLook, makeReal, thumb, type Look, type LookItem, type Product } from "@/lib/api";

const QUICK = ["Warmer and cosier", "Keep my sofa", "More plants", "Try Art Deco instead"];

const STAGES: Record<Look["status"], string> = {
  brief: "The stylist is looking at your room…",
  rendering: "Restyling your room, keeping your layout…",
  shopping: "Finding real products for the look…",
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
  return [look, setLook] as const;
}

function ProductRow({ p }: { p: Product }) {
  return (
    <a href={p.product_url} target="_blank" rel="noreferrer" className="flex min-w-0 flex-1 items-center gap-3">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={thumb(p.image_url)} alt="" className="size-12 shrink-0 rounded-lg bg-paper object-contain" />
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium">{p.name_en ?? p.name}</p>
        <p className="text-xs text-muted">{money(p.price_eur ?? p.price)}</p>
      </div>
    </a>
  );
}

function ItemCard({
  roomId,
  item,
  busy,
  onReal,
}: {
  roomId: string;
  item: LookItem;
  busy: boolean;
  onReal: (item: LookItem, product: Product) => void;
}) {
  const best = item.real ?? item.matches[0];
  return (
    <li className="pop-in flex gap-3 rounded-2xl bg-card p-3 ring-1 ring-line">
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={fileUrl(roomId, item.crop)} alt="" className="size-20 shrink-0 rounded-xl object-cover" />
      <div className="min-w-0 flex-1">
        <p className="text-sm font-medium">{item.description.name ?? item.concept}</p>
        <p className="truncate text-xs text-muted">
          {[item.description.color, item.description.material].filter(Boolean).join(" · ")}
        </p>
        {best ? (
          <div className="mt-2 flex items-center gap-2">
            <ProductRow p={best} />
            {item.real ? (
              <span className="shrink-0 rounded-full bg-ok/15 px-2 py-1 text-[11px] font-medium text-ok">In your room</span>
            ) : (
              <button
                disabled={busy}
                onClick={() => onReal(item, best)}
                className="shrink-0 rounded-full bg-ink px-3 py-1.5 text-xs font-medium text-white disabled:opacity-50"
              >
                Make it real
              </button>
            )}
          </div>
        ) : (
          <p className="mt-2 text-xs text-muted">No close match in our catalog yet</p>
        )}
      </div>
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
  const [look, setLook] = useLook(roomId, lookId);
  const [placing, setPlacing] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState("");

  async function onReal(item: LookItem, product: Product) {
    setPlacing(item.id);
    setError(null);
    try {
      setLook(await makeReal(roomId, lookId, item.id, product.id));
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setPlacing(null);
    }
  }

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
              {look.items.some((it) => it.view === i && placing === it.id) && " · placing the product…"}
            </figcaption>
          </figure>
        ))}
      </div>

      {look.items.length > 0 && (
        <section className="mt-8">
          <div className="flex items-baseline justify-between">
            <h2 className="text-lg font-semibold">Shop the look</h2>
            {look.shop.count > 0 && (
              <span className="text-sm tabular-nums text-muted">
                {look.shop.count} items · {money(look.shop.total)}
              </span>
            )}
          </div>
          <ul className="mt-3 space-y-3">
            {look.items.map((it) => (
              <ItemCard key={it.id} roomId={roomId} item={it} busy={placing !== null} onReal={onReal} />
            ))}
          </ul>
          {error && <p className="mt-2 text-sm text-warn">{error}</p>}
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
