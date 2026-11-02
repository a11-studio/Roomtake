// One icon set (Phosphor), one weight. Icons size with the text around them
// (1em) and take its color, so they sit inside buttons and pills like words.

import {
  ArrowUp as PhArrowUp,
  ArrowsLeftRight as PhArrowsLeftRight,
  Check as PhCheck,
  Plus as PhPlus,
  Shuffle as PhShuffle,
  X as PhX,
} from "@phosphor-icons/react";
import type { ComponentType } from "react";

type Props = { className?: string };

function icon(Glyph: ComponentType<{ size?: string; weight?: "bold"; className?: string; "aria-hidden"?: boolean }>) {
  const Icon = ({ className = "" }: Props) => (
    <Glyph size="1em" weight="bold" aria-hidden className={`shrink-0 ${className}`} />
  );
  return Icon;
}

/** "Surprise me": we pick a style for you, so the icon says pick-at-random, not "AI". */
export const Shuffle = icon(PhShuffle);
export const Plus = icon(PhPlus);
export const ArrowUp = icon(PhArrowUp);
export const ArrowsLeftRight = icon(PhArrowsLeftRight);
export const Check = icon(PhCheck);
export const Close = icon(PhX);
