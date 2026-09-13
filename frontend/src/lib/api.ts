import type {
  CaptionStyle,
  Decision,
  Options,
  ProjectRecord,
  ProjectSummary,
  ProjectView,
} from "./types";

export class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number,
  ) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { cache: "no-store", ...init });
  if (!response.ok) {
    let message = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (body?.detail) {
        message = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
      }
    } catch {
      // Not JSON; keep the status line.
    }
    throw new ApiError(message, response.status);
  }
  return (await response.json()) as T;
}

function postJson(body: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export function getOptions() {
  return request<Options>("/options");
}

export function listProjects() {
  return request<ProjectSummary[]>("/projects");
}

export function getProject(id: string) {
  return request<ProjectView>(`/projects/${id}`);
}

export interface NewProject {
  topic: string;
  styleRefKey?: string;
  voiceId?: string;
  imageModel?: string;
  imageQuality?: string;
  videoModel?: string;
  captionStyle?: CaptionStyle;
}

export function createProject(input: NewProject) {
  return request<ProjectRecord>(
    "/projects",
    postJson({
      topic: input.topic,
      style_ref_key: input.styleRefKey ?? null,
      voice_id: input.voiceId ?? null,
      image_model: input.imageModel ?? null,
      image_quality: input.imageQuality ?? null,
      video_model: input.videoModel ?? null,
      caption_style: input.captionStyle ?? null,
    }),
  );
}

export function decide(id: string, decision: Decision) {
  return request<{ accepted: boolean; stage: string }>(
    `/projects/${id}/decisions`,
    postJson(decision),
  );
}

export function retryProject(id: string) {
  return request<{ accepted: boolean }>(`/projects/${id}/retry`, { method: "POST" });
}

export function uploadImage(file: File) {
  const form = new FormData();
  form.append("file", file);
  return request<{ key: string; url: string }>("/uploads", { method: "POST", body: form });
}

export function assetUrl(view: ProjectView, key: string | null | undefined) {
  if (!key) return undefined;
  return view.assets[key] ?? `/files/${key}`;
}

/** Video URL that makes browsers show an early frame instead of a black box before playback. */
export function videoUrl(view: ProjectView, key: string | null | undefined) {
  const url = assetUrl(view, key);
  return url && `${url}#t=0.1`;
}

export function errorMessage(error: unknown) {
  return error instanceof Error ? error.message : String(error);
}

export function timeAgo(iso: string, now: number) {
  const seconds = Math.max(0, (now - new Date(iso).getTime()) / 1000);
  if (seconds < 60) return "just now";
  const units: [number, string][] = [
    [86400, "d"],
    [3600, "h"],
    [60, "m"],
  ];
  for (const [size, label] of units) {
    if (seconds >= size) return `${Math.floor(seconds / size)}${label} ago`;
  }
  return "just now";
}
