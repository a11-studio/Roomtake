// Small stroke/fill icons, sized by the parent's font size (1em) and coloured
// by currentColor, so they sit inside buttons like text.

type Props = { className?: string };

/** Four-point sparkle with a small companion: "let the AI pick". */
export function Spark({ className = "" }: Props) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="currentColor" aria-hidden className={className}>
      <path d="M11 2.5c.4 0 .7.3.8.7l.9 3.6a5 5 0 0 0 3.6 3.6l3.6.9a.8.8 0 0 1 0 1.6l-3.6.9a5 5 0 0 0-3.6 3.6l-.9 3.6a.8.8 0 0 1-1.6 0l-.9-3.6a5 5 0 0 0-3.6-3.6l-3.6-.9a.8.8 0 0 1 0-1.6l3.6-.9a5 5 0 0 0 3.6-3.6l.9-3.6c.1-.4.4-.7.8-.7Z" />
      <path d="M19 1.8c.2 0 .4.1.4.3l.3 1.1c.1.5.5.9 1 1l1.1.3a.4.4 0 0 1 0 .8l-1.1.3c-.5.1-.9.5-1 1l-.3 1.1a.4.4 0 0 1-.8 0l-.3-1.1c-.1-.5-.5-.9-1-1l-1.1-.3a.4.4 0 0 1 0-.8l1.1-.3c.5-.1.9-.5 1-1l.3-1.1c0-.2.2-.3.4-.3Z" />
    </svg>
  );
}

export function Plus({ className = "" }: Props) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" aria-hidden className={className}>
      <path d="M12 5v14M5 12h14" />
    </svg>
  );
}

export function ArrowUp({ className = "" }: Props) {
  return (
    <svg viewBox="0 0 24 24" width="1em" height="1em" fill="none" stroke="currentColor" strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" aria-hidden className={className}>
      <path d="M12 19V5M6 11l6-6 6 6" />
    </svg>
  );
}
