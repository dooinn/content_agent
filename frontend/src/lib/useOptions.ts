import { useEffect, useState } from "react";
import { getOptions } from "./api";
import type { Options } from "./types";

let cached: Options | null = null;

/** Model and caption choices from the backend, fetched once per page load. */
export function useOptions() {
  const [options, setOptions] = useState<Options | null>(cached);

  useEffect(() => {
    if (cached) return;
    let active = true;
    getOptions()
      .then((result) => {
        cached = result;
        if (active) setOptions(result);
      })
      .catch(() => {
        // The console still works with server defaults; pickers stay hidden.
      });
    return () => {
      active = false;
    };
  }, []);

  return options;
}
