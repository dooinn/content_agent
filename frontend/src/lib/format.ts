import type { ProjectState } from "./types";

/** 4.33 -> "0:04" */
export function mmss(seconds: number) {
  const whole = Math.max(0, Math.floor(seconds));
  return `${Math.floor(whole / 60)}:${String(whole % 60).padStart(2, "0")}`;
}

/** 30 -> "30 sec", 120 -> "2 min"; projects without a length are 30-second shorts. */
export function lengthLabel(seconds?: number | null) {
  const value = seconds ?? 30;
  return value < 60 ? `${value} sec` : `${value / 60} min`;
}

export function timeRange(start?: number, end?: number) {
  return start === undefined || end === undefined ? "" : `${mmss(start)}–${mmss(end)}`;
}

/** Storage key of the keyframe chosen for scene 1, used for thumbnails and caption previews. */
export function firstKeyframeKey(state: ProjectState) {
  const candidates = state.keyframes?.["1"];
  return candidates ? candidates[state.selected_keyframes?.["1"] ?? 0] : undefined;
}

export function sameJson(a: unknown, b: unknown) {
  return JSON.stringify(a) === JSON.stringify(b);
}
