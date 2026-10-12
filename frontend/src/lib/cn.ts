import { clsx, type ClassValue } from "clsx";
import { extendTailwindMerge } from "tailwind-merge";

// Teach tailwind-merge the design tokens: without this, custom font-size
// utilities (text-caption, text-label…) are mistaken for text colours and
// get dropped when a colour class follows.
const twMerge = extendTailwindMerge({
  extend: {
    classGroups: {
      "font-size": [
        { text: ["2xs", "brand", "caption", "label", "body", "lead", "section", "page", "page-wide", "balance", "hero", "hero-wide"] },
      ],
    },
  },
});

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
