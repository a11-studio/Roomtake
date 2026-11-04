// Matches backend/app/catalog/models.py STYLES.
export const STYLES: { name: string; hint: string; swatches: string[] }[] = [
  { name: "Scandinavian", hint: "Light oak, linen, bouclé", swatches: ["#efe8dc", "#c9a57d", "#9aa7a2"] },
  { name: "Japandi", hint: "Low, calm and earthy", swatches: ["#e6ddcf", "#8c7a64", "#3b3631"] },
  { name: "Art Deco", hint: "Velvet, brass, marble", swatches: ["#1f4d3e", "#c9a34e", "#1e2a44"] },
  { name: "Mid-Century", hint: "Walnut, mustard, olive", swatches: ["#8a5a3b", "#d4a23a", "#6b7f4e"] },
  { name: "Mediterranean", hint: "Rattan, terracotta, jute", swatches: ["#f3eee6", "#c56a42", "#b9a27c"] },
  // a season, not an interior: your own room dressed for the holidays
  { name: "Christmas", hint: "Tree, lights, candles", swatches: ["#24452f", "#a8322d", "#d4a94e"] },
];

/** A style worth trying next: a clear change of mood, never the one you have. */
export const CONTRAST: Record<string, string> = {
  Scandinavian: "Art Deco",
  Japandi: "Mediterranean",
  "Art Deco": "Japandi",
  "Mid-Century": "Scandinavian",
  Mediterranean: "Mid-Century",
  Christmas: "Scandinavian",
};

/** Which of our styles a look is in, from its title or the change that made it. */
export function styleOf(...texts: (string | null | undefined)[]): string | undefined {
  for (const t of texts) {
    const hit = t && STYLES.find((s) => t.toLowerCase().includes(s.name.toLowerCase()));
    if (hit) return hit.name;
  }
}
