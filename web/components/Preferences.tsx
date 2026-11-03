"use client";

import { useMemo, useState } from "react";
import { Count } from "@/components/Count";
import { Check, Plus, Shuffle } from "@/components/Icons";
import { fileUrl, type Preferences as Prefs, type Room } from "@/lib/api";
import { STYLES } from "@/lib/styles";

const BUDGET = { min: 300, max: 8000, step: 100 };

/** Two parts that read apart: what we found in your room (a quiet beige
 * block, read-only), then the choices for the new look (white, tappable). */
export function Preferences({
  roomId,
  room,
  busy,
  onSubmit,
}: {
  roomId: string;
  room: Room;
  busy: boolean;
  onSubmit: (p: Prefs) => void;
}) {
  const [style, setStyle] = useState<string | undefined>();
  const [budget, setBudget] = useState(2000);
  const [keep, setKeep] = useState<string[]>([]);

  // per kind, the most seen on one photo: the same sofa on two photos is one sofa
  const counts = useMemo(() => {
    const c = new Map<string, number>();
    room.objects
      .filter((o) => o.category !== "zone")
      .forEach((o) => c.set(`${o.label}|${o.best_frame}`, (c.get(`${o.label}|${o.best_frame}`) ?? 0) + 1));
    const best = new Map<string, number>();
    c.forEach((n, key) => {
      const label = key.split("|")[0];
      best.set(label, Math.max(best.get(label) ?? 0, n));
    });
    return [...best.entries()];
  }, [room]);
  // one chip per kind of furniture ("chair ×4" keeps all four)
  const furniture = useMemo(() => {
    const g = new Map<string, string[]>();
    room.objects
      .filter((o) => o.category === "furniture")
      .forEach((o) => g.set(o.label, [...(g.get(o.label) ?? []), o.id]));
    return [...g.entries()];
  }, [room]);
  const freeZone = room.views.find((v) => v.kind === "zone");
  const fill = ((budget - BUDGET.min) / (BUDGET.max - BUDGET.min)) * 100;

  return (
    <div className="pt-6">
      {/* full-width beige band: everything about the room as it is */}
      <section aria-label="Your room" className="bleed bg-veil pt-7 pb-9 lg:pt-10 lg:pb-12">
        <div className="mx-auto max-w-md px-5 md:max-w-3xl md:px-8 lg:max-w-6xl lg:px-10">
          <div className="flex items-baseline justify-between">
            <p className="eyebrow">Your room</p>
            <p className="text-xs text-muted">
              {room.views.length} {room.views.length === 1 ? "photo" : "photos"}
            </p>
          </div>
          <div className="-mx-5 mt-4 flex snap-x scroll-px-5 gap-3 overflow-x-auto px-5 [scrollbar-width:none] md:-mx-8 md:scroll-px-8 md:px-8 lg:mx-0 lg:scroll-px-0 lg:px-0">
            {room.keyframes.map((k) => (
              // eslint-disable-next-line @next/next/no-img-element
              <img
                key={k.file}
                src={fileUrl(roomId, k.file)}
                alt=""
                className="h-44 w-auto max-w-none shrink-0 snap-start rounded-2xl object-cover lg:h-52"
              />
            ))}
          </div>
          <h1 className="mt-7 text-[28px] font-semibold tracking-tight lg:text-[36px]">
            We found {counts.reduce((sum, [, n]) => sum + n, 0)} things
          </h1>
          <ul className="mt-4 flex flex-wrap gap-1.5">
            {counts.map(([label, n], i) => (
              // read-only: white and quiet, unlike the beige chips you can tap
              <li
                key={label}
                className={`pop-in inline-flex h-7 items-center gap-1.5 rounded-full bg-card pl-3 text-[13px] text-umber ${
                  n > 1 ? "pr-[5px]" : "pr-3"
                }`}
                style={{ animationDelay: `${i * 40}ms` }}
              >
                <span className="trim">{label}</span>
                {n > 1 && <Count n={n} quiet />}
              </li>
            ))}
            {freeZone && (
              <li className="pop-in inline-flex h-7 items-center gap-1.5 rounded-full border border-dashed border-[#a8957f] px-3 text-[13px] text-umber">
                <Plus className="text-[12px]" />
                <span className="trim">empty {freeZone.label.replace(" floor", "")} to furnish</span>
              </li>
            )}
          </ul>
        </div>
      </section>

      <div className="mt-10 lg:mt-14">
        <p className="eyebrow">Your new look</p>
        <h2 className="mt-2 text-[28px] font-semibold tracking-tight lg:text-[36px]">Pick a style</h2>
      </div>

      <div className="lg:grid lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-x-14">
        <div>
          <section className="mt-5">
            <div className="grid grid-cols-2 gap-3 md:grid-cols-3">
              {STYLES.map((s) => {
                const on = style === s.name;
                return (
                  <button
                    key={s.name}
                    onClick={() => setStyle(on ? undefined : s.name)}
                    aria-pressed={on}
                    className={`rounded-[20px] p-3.5 text-left transition-[background-color,box-shadow,transform] duration-200 active:scale-[0.98] ${
                      on
                        ? "bg-olive text-white shadow-[var(--shadow-float)]"
                        : "bg-card shadow-[var(--shadow-card)] hover:shadow-[var(--shadow-float)]"
                    }`}
                  >
                    <span className="flex">
                      {s.swatches.map((c, i) => (
                        <span
                          key={c}
                          className={`size-6 rounded-full ring-2 ${on ? "ring-olive" : "ring-card"} ${i ? "-ml-1.5" : ""}`}
                          style={{ background: c }}
                        />
                      ))}
                    </span>
                    <span className="mt-3 block text-[15px] font-medium">{s.name}</span>
                    <span className={`block text-xs ${on ? "text-white/70" : "text-muted"}`}>{s.hint}</span>
                  </button>
                );
              })}
            </div>
          </section>
        </div>

        <aside className="lg:mt-5 lg:self-start lg:rounded-3xl lg:p-7 lg:shadow-[var(--shadow-card)]">
          <section className="mt-10 lg:mt-0">
            <div className="flex items-baseline justify-between">
              <p className="eyebrow">Budget for real pieces</p>
              <span className="text-[15px] font-medium tabular-nums">€{budget.toLocaleString("en-IE")}</span>
            </div>
            <input
              type="range"
              min={BUDGET.min}
              max={BUDGET.max}
              step={BUDGET.step}
              value={budget}
              onChange={(e) => setBudget(Number(e.target.value))}
              className="range mt-5 w-full"
              style={{ ["--fill" as string]: `${fill}%` }}
              aria-label="Budget"
            />
          </section>

          <section className="mt-10">
            <p className="eyebrow">Keep as it is</p>
            <div className="mt-3 flex flex-wrap gap-2">
              {furniture.map(([label, ids]) => {
                const on = ids.every((i) => keep.includes(i));
                return (
                  <button
                    key={label}
                    onClick={() => setKeep(on ? keep.filter((k) => !ids.includes(k)) : [...new Set([...keep, ...ids])])}
                    aria-pressed={on}
                    className={`inline-flex h-9 items-center rounded-full pl-3.5 text-sm transition-[background-color,color,transform] duration-200 active:scale-95 ${
                      ids.length > 1 ? "pr-[9px]" : "pr-3.5"
                    } ${on ? "bg-olive text-white hover:bg-olive-deep" : "bg-veil hover:bg-[#d6cabd]"}`}
                  >
                    <span
                      // the check and its gap open together, so the label never jumps
                      className="grid overflow-hidden transition-[width,opacity] duration-300"
                      style={{
                        width: on ? 20 : 0,
                        opacity: on ? 1 : 0,
                        transitionTimingFunction: "var(--ease-travel)",
                      }}
                    >
                      <Check className="text-[14px]" />
                    </span>
                    <span className="trim">{label}</span>
                    {ids.length > 1 && (
                      <span className="ml-1.5 flex">
                        <Count n={ids.length} inverted={on} />
                      </span>
                    )}
                  </button>
                );
              })}
            </div>
          </section>

          <div className="sticky bottom-4 mt-12 lg:static lg:mt-10">
            <button
              onClick={() => onSubmit({ style, budget, keep })}
              disabled={busy}
              className="flex h-14 w-full items-center justify-center gap-2 rounded-full bg-olive text-base font-medium text-white shadow-[var(--shadow-float)] transition-[background-color,transform] hover:bg-olive-deep active:scale-[0.99] disabled:opacity-80"
            >
              {busy ? (
                "Starting…"
              ) : style ? (
                `Show my room in ${style}`
              ) : (
                <>
                  <Shuffle className="text-[18px]" />
                  Surprise me with a style
                </>
              )}
            </button>
          </div>
          <p className="mt-3 text-center text-xs text-muted">Same room, same layout, new look · about a minute</p>
        </aside>
      </div>
    </div>
  );
}
