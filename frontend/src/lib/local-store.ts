"use client";

import { useCallback, useSyncExternalStore } from "react";

/** Only two keys are ever persisted: the theme and the active team id. */
export const STORAGE_KEYS = {
  theme: "vip.theme",
  activeOrg: "vip.activeOrg",
} as const;

const EVENT = "vip:storage";

export function readStorage(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return null;
  }
}

export function writeStorage(key: string, value: string | null) {
  try {
    if (value === null) window.localStorage.removeItem(key);
    else window.localStorage.setItem(key, value);
  } catch {
    /* storage may be unavailable (private mode); the UI still works */
  }
  window.dispatchEvent(new Event(EVENT));
}

function subscribe(cb: () => void) {
  window.addEventListener(EVENT, cb);
  window.addEventListener("storage", cb);
  return () => {
    window.removeEventListener(EVENT, cb);
    window.removeEventListener("storage", cb);
  };
}

/** SSR-safe localStorage binding (server snapshot is always null). */
export function useStoredValue(key: string): [string | null, (v: string | null) => void] {
  const value = useSyncExternalStore(
    subscribe,
    () => readStorage(key),
    () => null,
  );
  const set = useCallback((v: string | null) => writeStorage(key, v), [key]);
  return [value, set];
}
