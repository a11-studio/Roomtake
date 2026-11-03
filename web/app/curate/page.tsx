"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Close } from "@/components/Icons";
import { getCatalog, importProduct, thumb, removeProduct, saveProduct, type Catalog, type Product } from "@/lib/api";

// What looks need most often: the pieces SAM finds in a restyled room.
const KEY_CATEGORIES = [
  "sofa",
  "armchair",
  "chair",
  "coffee table",
  "side table",
  "rug",
  "lamp",
  "shelving unit",
  "potted plant",
  "curtain",
  "cushion",
  "outdoor furniture",
  "painting",
  "mirror",
  "vase",
];
const TARGET = 4;

const eur = (n: number) => n.toLocaleString("en-IE", { style: "currency", currency: "EUR", maximumFractionDigits: 0 });
const size = (p: Product) =>
  [p.width_cm, p.depth_cm, p.height_cm].every((v) => v == null)
    ? "no size"
    : `${p.width_cm ?? "?"} × ${p.depth_cm ?? "?"} × ${p.height_cm ?? "?"} cm`;

/** Hand-pick Westwing products: paste a product URL, check what Spark filled in, save. */
export default function Curate() {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [url, setUrl] = useState("");
  const [variants, setVariants] = useState<Product[]>([]);
  const [draft, setDraft] = useState<Product | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = () =>
    getCatalog()
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  useEffect(() => {
    getCatalog()
      .then(setCatalog)
      .catch((e) => setError(String(e)));
  }, []);

  async function run(label: string, fn: () => Promise<void>) {
    setBusy(label);
    setError(null);
    try {
      await fn();
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(null);
    }
  }

  const onImport = () =>
    run("Reading the page…", async () => {
      const { variants } = await importProduct(url.trim());
      setVariants(variants);
      setDraft(variants[0]);
    });
  const onSave = () =>
    run("Saving…", async () => {
      if (!draft) return;
      await saveProduct(draft);
      setDraft(null);
      setVariants([]);
      setUrl("");
      await refresh();
    });
  const onRemove = (id: string) =>
    run("Removing…", async () => {
      await removeProduct(id);
      await refresh();
    });

  const westwing = catalog?.source === "westwing";
  const styles = catalog?.styles ?? [];
  const draftStyles =
    draft?.style
      ?.split(",")
      .map((s) => s.trim())
      .filter(Boolean) ?? [];

  return (
    <div className="pt-5">
      <header className="flex items-center justify-between">
        <Link href="/">
          <Image src="/RoomTake-light.svg" alt="Roomtake" width={46} height={36} />
        </Link>
        <span className="text-sm text-muted">Catalog</span>
      </header>

      <h1 className="mt-6 text-2xl font-semibold">Pick products</h1>
      <p className="mt-1 text-sm text-muted">
        Paste a Westwing product link (westwing.sk for EUR). We read the page, Muse Spark fills in category, English
        name and style from the photo; you check and save.
        {!westwing && " Until the first product is saved, the app uses the DummyJSON test catalog."}
      </p>
      {catalog && !catalog.editable && <p className="mt-3 text-sm text-warn">Editing is disabled on this server.</p>}

      <section className="mt-5 grid grid-cols-2 gap-1.5 text-xs">
        {KEY_CATEGORIES.map((c) => {
          const n = westwing ? (catalog?.counts[c] ?? 0) : 0;
          return (
            <div key={c} className="flex justify-between rounded-lg bg-card px-2.5 py-1.5 ring-1 ring-line">
              <span>{c}</span>
              <span className={n >= TARGET ? "text-ok" : n ? "" : "text-warn"}>
                {n}/{TARGET}
              </span>
            </div>
          );
        })}
      </section>

      <form
        className="mt-6 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (url.trim()) onImport();
        }}
      >
        <input
          value={url}
          onChange={(e) => setUrl(e.target.value)}
          placeholder="https://www.westwing.sk/…"
          className="min-w-0 flex-1 rounded-full bg-card px-4 py-2.5 text-sm outline-none ring-1 ring-line focus:ring-brand-strong"
        />
        <button
          disabled={!!busy}
          className="rounded-full bg-ink px-5 text-sm font-medium text-white disabled:opacity-50"
        >
          Import
        </button>
      </form>
      {busy && <p className="mt-2 text-sm text-muted">{busy}</p>}
      {error && <p className="mt-2 text-sm text-warn">{error}</p>}

      {draft && (
        <section className="pop-in mt-4 rounded-2xl bg-card p-4 ring-1 ring-line">
          <div className="flex gap-3">
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src={thumb(draft.image_url)} alt="" className="size-24 shrink-0 rounded-xl bg-paper object-contain" />
            <div className="min-w-0 text-sm">
              <p className="font-medium">{draft.name}</p>
              <p className="mt-1 text-muted">
                {eur(draft.price_eur)} · {size(draft)}
              </p>
              <p className="text-muted">{[draft.color, draft.material].filter(Boolean).join(" · ")}</p>
            </div>
          </div>

          {variants.length > 1 && (
            <select
              value={draft.id}
              onChange={(e) =>
                setDraft({
                  ...variants.find((v) => v.id === e.target.value)!,
                  category: draft.category,
                  style: draft.style,
                  name_en: draft.name_en,
                })
              }
              className="mt-3 w-full rounded-lg bg-paper px-2 py-2 text-sm ring-1 ring-line"
            >
              {variants.map((v) => (
                <option key={v.id} value={v.id}>
                  {v.name.split(" – ").slice(1).join(" – ") || v.name} · {eur(v.price_eur)}
                </option>
              ))}
            </select>
          )}

          <label className="mt-3 block text-xs text-muted">
            English name
            <input
              value={draft.name_en ?? ""}
              onChange={(e) => setDraft({ ...draft, name_en: e.target.value })}
              className="mt-1 w-full rounded-lg bg-paper px-2 py-2 text-sm text-ink ring-1 ring-line"
            />
          </label>
          <label className="mt-3 block text-xs text-muted">
            Category
            <select
              value={draft.category}
              onChange={(e) => setDraft({ ...draft, category: e.target.value })}
              className="mt-1 w-full rounded-lg bg-paper px-2 py-2 text-sm text-ink ring-1 ring-line"
            >
              {catalog?.categories.map((c) => (
                <option key={c}>{c}</option>
              ))}
            </select>
          </label>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {styles.map((s) => {
              const on = draftStyles.includes(s);
              return (
                <button
                  key={s}
                  onClick={() =>
                    setDraft({
                      ...draft,
                      style: (on ? draftStyles.filter((x) => x !== s) : [...draftStyles, s]).join(", ") || null,
                    })
                  }
                  className={`rounded-full px-2.5 py-1 text-xs ring-1 ${on ? "bg-ink text-white ring-ink" : "bg-veil ring-transparent"}`}
                >
                  {s}
                </button>
              );
            })}
          </div>
          <button
            onClick={onSave}
            disabled={!!busy}
            className="mt-4 w-full rounded-full bg-ink py-3 text-sm font-medium text-white disabled:opacity-50"
          >
            Save to catalog
          </button>
        </section>
      )}

      {westwing && (
        <section className="mt-8 space-y-6">
          {KEY_CATEGORIES.concat(catalog!.categories.filter((c) => !KEY_CATEGORIES.includes(c)))
            .filter((c) => catalog!.counts[c])
            .map((c) => (
              <div key={c}>
                <h2 className="text-sm font-medium">{c}</h2>
                <ul className="mt-2 space-y-2">
                  {catalog!.products
                    .filter((p) => p.category === c)
                    .map((p) => (
                      <li key={p.id} className="flex items-center gap-3 rounded-xl bg-card p-2 ring-1 ring-line">
                        {/* eslint-disable-next-line @next/next/no-img-element */}
                        <img
                          src={thumb(p.image_url)}
                          alt=""
                          className="size-12 shrink-0 rounded-lg bg-paper object-contain"
                        />
                        <a href={p.product_url} target="_blank" rel="noreferrer" className="min-w-0 flex-1">
                          <p className="truncate text-sm">{p.name_en ?? p.name}</p>
                          <p className="truncate text-xs text-muted">
                            {eur(p.price_eur)} · {p.style ?? "no style"}
                          </p>
                        </a>
                        <button
                          onClick={() => onRemove(p.id)}
                          disabled={!!busy}
                          aria-label={`Remove ${p.name_en ?? p.name}`}
                          className="px-2 text-lg text-muted"
                        >
                          <Close />
                        </button>
                      </li>
                    ))}
                </ul>
              </div>
            ))}
        </section>
      )}
    </div>
  );
}
