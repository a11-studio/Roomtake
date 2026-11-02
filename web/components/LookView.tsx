"use client";

import { useEffect, useState } from "react";
import { BeforeAfter } from "@/components/BeforeAfter";
import { ArrowUp } from "@/components/Icons";
import { Orb } from "@/components/Orb";
import { fileUrl, getLook, thumb, type Look, type ProductUse } from "@/lib/api";

const QUICK = ["Warmer and cosier", "Keep my sofa", "More plants", "Try Art Deco instead"];

const STEPS: { status: Look["status"]; label: string; hint: string }[] = [
  { status: "brief", label: "Reading your room", hint: "The stylist picks a direction and real pieces that fit" },
  { status: "rendering", label: "Drawing your new room", hint: "Same walls, same layout, new everything else" },
  { status: "checking", label: "Checking the layout", hint: "Making sure every piece stayed in its place" },
];
const ORDER: Look["status"][] = ["brief", "rendering", "checking", "done"];

const money = (n: number | undefined) =>
  (n ?? 0).toLocaleString("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });

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

function useElapsed() {
  const [start] = useState(() => Date.now());
  const [now, setNow] = useState(start);
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  return Math.round((now - start) / 1000);
}

/** Only the step that is running, its title shimmering like a model thinking. */
function Progress({ status }: { status: Look["status"] }) {
  const elapsed = useElapsed();
  const at = Math.max(0, ORDER.indexOf(status));
  const step = STEPS[Math.min(at, STEPS.length - 1)];
  return (
    <section className="mt-8 flex items-center gap-4 rounded-3xl bg-[#f7f4f1] p-4 pr-5">
      <Orb className="size-11" active />
      <div key={step.status} className="pop-in min-w-0 flex-1">
        <p className="thinking text-[17px] font-medium">{step.label}</p>
        <p className="mt-0.5 text-sm text-muted">{step.hint}</p>
      </div>
      <span className="self-start pt-1 text-xs text-muted tabular-nums">
        {at + 1}/{STEPS.length} · {elapsed}s
      </span>
    </section>
  );
}

function UsedProduct({ use, index }: { use: ProductUse; index: number }) {
  const p = use.product;
  const where = use.for === "add" ? "Added" : `New ${use.for}`;
  return (
    <li
      className="pop-in flex items-center gap-4 rounded-2xl bg-card p-3 pr-4 shadow-[var(--shadow-card)]"
      style={{ animationDelay: `${index * 60}ms` }}
    >
      {/* eslint-disable-next-line @next/next/no-img-element */}
      <img src={thumb(p.image_url)} alt="" className="size-16 shrink-0 rounded-xl bg-[#f6f5f3] object-contain p-1" />
      <div className="min-w-0 flex-1">
        <p className="eyebrow !text-[10px]">
          {where}
          {use.view !== "main" && ` · ${use.view.replace(" floor", "")}`}
        </p>
        <p className="mt-0.5 truncate text-[15px] font-medium">{p.name_en ?? p.name}</p>
        <p className="text-sm text-muted tabular-nums">{money(p.price_eur ?? p.price)}</p>
      </div>
      <a
        href={p.product_url}
        target="_blank"
        rel="noreferrer"
        className="shrink-0 rounded-full bg-ink px-4 py-2 text-sm font-medium text-white transition active:scale-95"
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
  const [more, setMore] = useState(false);

  if (!look) {
    return (
      <div className="pt-10">
        <span className="shimmer block h-4 w-32 rounded-full bg-veil" />
        <span className="shimmer mt-4 block h-8 w-56 rounded-full bg-veil" />
        <span className="shimmer mt-8 block aspect-video w-full rounded-3xl bg-veil" />
      </div>
    );
  }
  const working = look.status !== "done" && look.status !== "error";
  const products = look.products ?? [];

  // Phone: header, views, details stacked. Desktop: views on the left, header
  // and details in a column on the right.
  return (
    <div className="pt-8 lg:grid lg:grid-cols-[minmax(0,1fr)_400px] lg:gap-x-14 lg:pt-10">
      <header className="lg:col-start-2 lg:row-start-1">
        <p className="eyebrow">{look.instruction ? `“${look.instruction}”` : "Your room, restyled"}</p>
        {look.brief ? (
          <>
            <h1 className="pop-in mt-2 text-[30px] font-semibold leading-tight tracking-tight lg:text-[36px]">
              {look.brief.title}
            </h1>
            <p className={`pop-in mt-3 text-[15px] leading-relaxed text-muted ${more ? "" : "line-clamp-3"}`}>
              {look.brief.why ?? look.brief.summary}
            </p>
            {!more && (
              <button
                onClick={() => setMore(true)}
                className="mt-1 text-sm font-medium underline-offset-4 hover:underline"
              >
                Read more
              </button>
            )}
            {look.brief.palette && (
              <ul className="pop-in mt-4 flex flex-wrap gap-1.5">
                {[...new Set(look.brief.palette)].slice(0, 5).map((p) => (
                  <li key={p} className="rounded-full bg-veil px-3 py-1 text-xs">
                    {p}
                  </li>
                ))}
              </ul>
            )}
          </>
        ) : (
          <h1 className="mt-2 text-[30px] font-semibold tracking-tight lg:text-[36px]">Designing your look</h1>
        )}

        {working && <Progress status={look.status} />}
        {look.status === "error" && (
          <p className="mt-8 rounded-2xl bg-card p-4 text-sm text-warn shadow-[var(--shadow-card)]">
            Something went wrong: {look.error}
          </p>
        )}
      </header>

      <div className="mt-8 space-y-6 lg:col-start-1 lg:row-span-2 lg:row-start-1 lg:mt-0">
        {look.views.map((v, i) => (
          <figure key={v.file}>
            <div className="overflow-hidden rounded-3xl shadow-[var(--shadow-card)]">
              {v.current ? (
                <BeforeAfter before={fileUrl(roomId, v.file)} after={fileUrl(roomId, v.current)} alt={v.label} />
              ) : (
                <div className="shimmer relative">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img
                    src={fileUrl(roomId, v.file)}
                    alt=""
                    className="aspect-video w-full object-cover opacity-80 blur-[1px]"
                  />
                  <span className="absolute bottom-3 left-3 rounded-full bg-card/90 px-3 py-1 text-xs font-medium">
                    {i === 0 ? "Restyling…" : "Furnishing…"}
                  </span>
                </div>
              )}
            </div>
            <figcaption className="mt-2 px-1 text-xs text-muted">
              {v.kind === "main" ? "Your room" : `Your ${v.label.replace(" floor", "")}`}
              {v.current && " · drag to compare"}
            </figcaption>
          </figure>
        ))}
      </div>

      {look.status === "done" && (
        <div className="lg:col-start-2 lg:row-start-2">
          <section className="mt-12 lg:mt-10">
            <div className="flex items-baseline justify-between">
              <p className="eyebrow">Real pieces in this design</p>
              {look.shop.count > 0 && (
                <span className="text-[15px] font-medium tabular-nums">{money(look.shop.total)}</span>
              )}
            </div>
            {products.length > 0 ? (
              <>
                <p className="mt-2 text-sm leading-relaxed text-muted">
                  Real Westwing products, drawn into your photo. Everything else is a design idea.
                </p>
                <ul className="mt-4 space-y-3">
                  {products.map((u, i) => (
                    <UsedProduct key={u.product.id} use={u} index={i} />
                  ))}
                </ul>
              </>
            ) : (
              <p className="mt-2 text-sm text-muted">
                Nothing in our catalog fits this look yet, so every piece is a design idea.
              </p>
            )}
          </section>

          <section className="mt-12">
            <p className="eyebrow">Try a change</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {QUICK.map((q) => (
                <button
                  key={q}
                  disabled={busy}
                  onClick={() => onRevise(q)}
                  className="rounded-full bg-veil px-3.5 py-2 text-sm transition active:scale-95 disabled:opacity-50"
                >
                  {q}
                </button>
              ))}
            </div>
            <form
              className="mt-4 flex items-center gap-2 rounded-full bg-card p-1.5 pl-2 shadow-[var(--shadow-card)] ring-1 ring-line"
              onSubmit={(e) => {
                e.preventDefault();
                if (text.trim()) onRevise(text.trim());
                setText("");
              }}
            >
              <Orb className="size-9" active={busy || !!text.trim()} />
              <input
                value={text}
                onChange={(e) => setText(e.target.value)}
                disabled={busy}
                placeholder="Tell the stylist what to change"
                className="min-w-0 flex-1 rounded-2xl bg-transparent px-1.5 py-3 text-[15px] outline-none placeholder:text-muted/70"
              />
              <button
                disabled={busy || !text.trim()}
                aria-label="Send"
                className="grid size-11 shrink-0 place-items-center rounded-full bg-ink text-lg text-white transition active:scale-95 disabled:opacity-30"
              >
                <ArrowUp />
              </button>
            </form>
          </section>
        </div>
      )}
    </div>
  );
}
