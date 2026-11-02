"use client";

import { useMemo, useState } from "react";
import { Spark } from "@/components/Icons";
import { fileUrl, type Preferences as Prefs, type Room } from "@/lib/api";

// Matches backend/app/catalog/models.py STYLES.
const STYLES: { name: string; hint: string; swatches: string[] }[] = [
  { name: "Scandinavian", hint: "Light oak, linen, bouclé", swatches: ["#efe8dc", "#c9a57d", "#9aa7a2"] },
  { name: "Japandi", hint: "Low, calm and earthy", swatches: ["#e6ddcf", "#8c7a64", "#3b3631"] },
  { name: "Art Deco", hint: "Velvet, brass, marble", swatches: ["#1f4d3e", "#c9a34e", "#1e2a44"] },
  { name: "Mid-Century", hint: "Walnut, mustard, olive", swatches: ["#8a5a3b", "#d4a23a", "#6b7f4e"] },
  { name: "Mediterranean", hint: "Rattan, terracotta, jute", swatches: ["#f3eee6", "#c56a42", "#b9a27c"] },
];

const BUDGET = { min: 300, max: 8000, step: 100 };

/** Room summary + the three quick choices before the stylist runs. */
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

  const counts = useMemo(() => {
    const c = new Map<string, number>();
    room.objects.filter((o) => o.category !== "zone").forEach((o) => c.set(o.label, (c.get(o.label) ?? 0) + 1));
    return [...c.entries()];
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
    <div className="pt-6 lg:pt-10">
      <div className="-mx-5 flex snap-x gap-3 overflow-x-auto px-5 pb-1 [scrollbar-width:none] md:-mx-8 md:px-8 lg:mx-0 lg:px-0">
        {room.keyframes.map((k) => (
          // eslint-disable-next-line @next/next/no-img-element
          <img
            key={k.file}
            src={fileUrl(roomId, k.file)}
            alt=""
            className="aspect-[4/3] w-60 shrink-0 snap-start rounded-2xl object-cover shadow-[var(--shadow-card)] lg:w-72"
          />
        ))}
      </div>

      <div className="lg:mt-4 lg:grid lg:grid-cols-[minmax(0,1fr)_380px] lg:gap-x-14">
        <div>
          <section className="mt-8">
            <p className="eyebrow">Your room</p>
            <h1 className="mt-2 text-[28px] font-semibold tracking-tight lg:text-[36px]">
              We found {room.objects.length} things
            </h1>
            <ul className="mt-4 flex flex-wrap gap-1.5">
              {counts.map(([label, n], i) => (
                <li
                  key={label}
                  className="pop-in flex items-center gap-1.5 rounded-full bg-[#f4efe9] py-1 pr-3 pl-3 text-[13px]"
                  style={{ animationDelay: `${i * 25}ms` }}
                >
                  {label}
                  {n > 1 && (
                    <span className="grid h-[18px] min-w-[18px] place-items-center rounded-full bg-card px-1 text-[11px] font-medium text-muted tabular-nums">
                      {n}
                    </span>
                  )}
                </li>
              ))}
              {freeZone && (
                <li className="pop-in rounded-full border border-dashed border-[#c9b9a7] px-3 py-[3px] text-[13px] text-muted">
                  + empty {freeZone.label.replace(" floor", "")}, ready for something new
                </li>
              )}
            </ul>
          </section>

          <section className="mt-10">
            <p className="eyebrow">Style</p>
            <div className="mt-3 grid grid-cols-2 gap-3 md:grid-cols-3">
              {STYLES.map((s) => {
                const on = style === s.name;
                return (
                  <button
                    key={s.name}
                    onClick={() => setStyle(on ? undefined : s.name)}
                    aria-pressed={on}
                    className={`rounded-2xl p-3.5 text-left transition active:scale-[0.98] ${
                      on ? "bg-ink text-white shadow-[var(--shadow-float)]" : "bg-card shadow-[var(--shadow-card)]"
                    }`}
                  >
                    <span className="flex">
                      {s.swatches.map((c, i) => (
                        <span
                          key={c}
                          className={`size-6 rounded-full ring-2 ${on ? "ring-ink" : "ring-card"} ${i ? "-ml-1.5" : ""}`}
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

        <aside className="lg:mt-8 lg:self-start lg:rounded-3xl lg:bg-[#f7f4f1] lg:p-7">
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
                    className={`rounded-full px-3.5 py-2 text-sm transition ${on ? "bg-ink text-white" : "bg-veil"}`}
                  >
                    {on && "✓ "}
                    {label}
                    {ids.length > 1 && <span className={on ? "text-white/60" : "text-muted"}> ×{ids.length}</span>}
                  </button>
                );
              })}
            </div>
          </section>

          <div className="sticky bottom-4 mt-12 lg:static lg:mt-10">
            <button
              onClick={() => onSubmit({ style, budget, keep })}
              disabled={busy}
              className="flex w-full items-center justify-center gap-2 rounded-full bg-ink py-4 text-base font-medium text-white shadow-[var(--shadow-float)] transition active:scale-[0.99] disabled:opacity-80"
            >
              {busy ? (
                "Starting…"
              ) : style ? (
                `Show my room in ${style}`
              ) : (
                <>
                  <Spark className="text-[18px]" />
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
