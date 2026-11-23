/** "× Melli" beside the logo on a store's demo link. */
export function StoreTag({ name }: { name: string }) {
  return (
    <span className="inline-flex h-8 items-center gap-2 rounded-full bg-card px-3.5 text-sm font-medium shadow-[var(--shadow-card)]">
      <span className="text-muted">×</span>
      {name}
    </span>
  );
}
