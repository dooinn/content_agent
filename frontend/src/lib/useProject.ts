import { useCallback, useEffect, useState } from "react";
import { errorMessage, getProject } from "./api";
import type { ProjectView } from "./types";

const POLL_MS = 3000;

/** Loads a project and keeps it fresh while the backend works in the background. */
export function useProject(id: string) {
  const [view, setView] = useState<ProjectView | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setView(await getProject(id));
      setError(null);
    } catch (err) {
      setError(errorMessage(err));
    }
  }, [id]);

  useEffect(() => {
    let active = true;
    const load = async () => {
      if (active) await refresh();
    };
    load();
    const timer = setInterval(load, POLL_MS);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, [refresh]);

  return { view, error, refresh };
}
