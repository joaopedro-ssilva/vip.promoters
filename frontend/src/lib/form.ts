import type { FieldValues, Path, UseFormSetError } from "react-hook-form";
import { ApiError } from "./api/client";

/**
 * Maps a server error onto react-hook-form.
 * - `fields` (422) are attached to the matching form fields (optionally renamed via `map`)
 * - anything else (or fields that have no matching input) is returned as a
 *   general message to render at the top of the form.
 */
export function applyServerError<T extends FieldValues>(
  err: unknown,
  setError: UseFormSetError<T>,
  known: readonly string[],
  map: Record<string, string> = {},
): string | null {
  if (!(err instanceof ApiError)) {
    return "Algo deu errado. Tente novamente.";
  }
  if (err.fields && Object.keys(err.fields).length > 0) {
    const leftovers: string[] = [];
    for (const [key, message] of Object.entries(err.fields)) {
      const name = map[key] ?? key;
      if (known.includes(name)) {
        setError(name as Path<T>, { type: "server", message });
      } else {
        leftovers.push(message);
      }
    }
    return leftovers.length > 0 ? leftovers.join(" ") : null;
  }
  if (err.code === "rate_limited" && err.retryAfter) {
    return `${err.message} Tente novamente em ${err.retryAfter} s.`;
  }
  return err.message;
}
