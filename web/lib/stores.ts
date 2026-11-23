// Furniture stores with their own demo link (/?store=melli). Rooms made from it
// are styled only with that store's products (backend STORES, app/catalog).
// demoRoom: a ready room styled with their products, for "Try our demo".
export const STORES: Record<string, { name: string; demoRoom?: string }> = {
  melli: { name: "Melli", demoRoom: "melli_demo" },
};

/** The store in the page address, if it is one we know. */
export function storeFromUrl(): string | null {
  const s = new URLSearchParams(window.location.search).get("store");
  return s && s in STORES ? s : null;
}
