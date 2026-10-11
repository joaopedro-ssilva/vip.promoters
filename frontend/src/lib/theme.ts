"use client";

import { useCallback, useSyncExternalStore } from "react";
import { STORAGE_KEYS, writeStorage } from "./local-store";

export type Theme = "dark" | "light";

/** Inline script executed before first paint (see root layout). Static string, no data. */
export const THEME_INIT_SCRIPT = `try{var t=localStorage.getItem(${JSON.stringify(
  STORAGE_KEYS.theme,
)});if(t==="light"){document.documentElement.setAttribute("data-theme","light")}}catch(e){}`;

function subscribe(cb: () => void) {
  const obs = new MutationObserver(cb);
  obs.observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
  return () => obs.disconnect();
}

function getSnapshot(): Theme {
  return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
}

export function useTheme(): [Theme, (t: Theme) => void] {
  const theme = useSyncExternalStore(subscribe, getSnapshot, () => "dark" as Theme);
  const set = useCallback((t: Theme) => {
    if (t === "light") document.documentElement.setAttribute("data-theme", "light");
    else document.documentElement.removeAttribute("data-theme");
    writeStorage(STORAGE_KEYS.theme, t);
  }, []);
  return [theme, set];
}
