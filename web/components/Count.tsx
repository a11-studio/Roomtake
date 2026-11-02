/** A small count inside a pill ("chair 4"). Sized so that in a 28px pill it sits
 * 5px from the top, bottom and end: nested shapes pad evenly. */
export function Count({ n, inverted = false }: { n: number; inverted?: boolean }) {
  return (
    <span
      className={`grid h-[18px] min-w-[18px] shrink-0 place-items-center rounded-full px-1 text-[11px] font-medium tabular-nums ${
        inverted ? "bg-white/15 text-white" : "bg-card text-muted"
      }`}
    >
      <span className="trim">{n}</span>
    </span>
  );
}
