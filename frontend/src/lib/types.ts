// Shapes returned by the FastAPI backend (backend/app/api/routes.py and graph/pipeline.py).

export type Status =
  | "running"
  | "awaiting_review"
  | "failed"
  | "rejected"
  | "preview_ready"
  | "final_ready"
  | "done";

export type Stage =
  | "research"
  | "angle"
  | "script"
  | "audio"
  | "bible"
  | "scenes"
  | "keyframes"
  | "preview"
  | "motion"
  | "clips"
  | "final";

export interface ProjectRecord {
  id: string;
  topic: string;
  status: Status;
  stage: string | null;
  error: string | null;
  thumbnail_key?: string | null;
  created_at: string;
  updated_at: string;
}

export interface ProjectSummary extends ProjectRecord {
  thumbnail_url: string | null;
}

export type CaptionPosition = "bottom" | "lower-third" | "center";

export interface CaptionStyle {
  font: string;
  size: number;
  position: CaptionPosition;
  uppercase: boolean;
}

export interface ModelOption {
  id: string;
  label: string;
  note: string;
}

export interface Options {
  image_models: ModelOption[];
  image_qualities: string[];
  video_models: ModelOption[];
  caption_fonts: { id: string; label: string }[];
  caption_positions: { id: CaptionPosition; label: string }[];
  caption_size: { min: number; max: number };
  defaults: {
    image_model: string;
    image_quality: string;
    video_model: string;
    caption_style: CaptionStyle;
  };
}

export interface Source {
  id: string;
  title: string;
  url: string;
  tier?: "scholarly" | "reference" | "popular";
}

export interface Fact {
  id: string;
  claim: string;
  status: "verified" | "disputed" | "legend";
  source_ids: string[];
  note: string;
}

export interface FactSheet {
  figure: string;
  born: string;
  died: string;
  death_year: number | null;
  era: string;
  region: string;
  summary: string;
  appearance_notes: string;
  costume_notes: string;
  setting_notes: string;
  facts: Fact[];
  sources: Source[];
}

export interface FactCheckReport {
  passed: boolean;
  issues: { location: string; claim: string; problem: string; suggested_fix: string }[];
}

export interface StoryAngle {
  title: string;
  hook_line: string;
  logline: string;
  fact_ids: string[];
  why_it_works: string;
  accuracy_notes: string;
}

export interface Script {
  title: string;
  segments: { beat: string; narration: string; fact_ids: string[] }[];
}

export interface Narration {
  audio_key: string;
  voice_id: string;
  duration: number;
  segments: { order: number; start: number; end: number }[];
}

export interface Bgm {
  audio_key: string;
  prompt: string;
  seconds: number;
}

export interface CharacterLook {
  id: string;
  label: string;
  age: string;
  physical_description: string;
  costume: string;
  sheet_prompt: string;
}

export interface StyleBible {
  visual_style: string;
  color_palette: string;
  lighting: string;
  period_details: string[];
  anachronisms_to_avoid: string[];
  character: { name: string; signature_props: string[]; looks?: CharacterLook[] };
}

export interface Scene {
  order: number;
  description: string;
  shot_type: string;
  camera_move: string;
  character_look?: string | null;
  image_prompt: string;
  narration: string;
  start: number;
  end: number;
  video_prompt?: string;
  clip_seconds?: number;
}

export interface CriticReport {
  passed: boolean;
  issues: { scene_order: number; category: string; detail: string; suggested_fix: string }[];
}

export interface Shot {
  order: number;
  narration: string;
  video_prompt: string;
  clip_seconds: number;
}

export interface ProjectState {
  topic?: string;
  script?: Script;
  narration?: Narration;
  bible?: StyleBible;
  style_ref_key?: string | null;
  scenes?: Scene[];
  keyframes?: Record<string, string[]>;
  selected_keyframes?: Record<string, number>;
  character_refs?: Record<string, string>;
  clips?: Record<string, string[]>;
  selected_clips?: Record<string, number>;
  preview_key?: string;
  final_key?: string;
  image_model?: string | null;
  image_quality?: string | null;
  video_model?: string | null;
  caption_style?: CaptionStyle | null;
}

export interface ProjectView {
  project: ProjectRecord;
  running: boolean;
  stage: Stage | null;
  payload: unknown;
  state: ProjectState;
  assets: Record<string, string>;
}

export interface Decision {
  action: "approve" | "revise" | "select" | "regenerate";
  feedback?: string;
  choice?: number;
  scene_orders?: number[];
  edits?: Record<string, unknown>;
}

// ------------------------------------------------------------ review payloads per stage

export interface ResearchPayload {
  fact_sheet: FactSheet;
  eligibility: { ok: boolean; reason: string };
}

export interface AnglePayload {
  angles: StoryAngle[];
  fact_check: FactCheckReport | null;
}

export interface ScriptPayload {
  script: Script;
  word_count: number;
  estimated_seconds: number;
  fact_check: FactCheckReport | null;
}

export interface AudioPayload {
  narration: Narration;
  bgm: Bgm;
}

export interface BiblePayload {
  bible: StyleBible;
  character_refs: Record<string, string>;
}

export interface ScenesPayload {
  scenes: Scene[];
  critic_report: CriticReport | null;
  critic_rounds: number;
}

export interface KeyframesPayload {
  scenes: (Pick<Scene, "order" | "narration" | "image_prompt"> & { start?: number; end?: number })[];
  keyframes: Record<string, string[]>;
  selected: Record<string, number>;
  image_model?: string;
  image_quality?: string;
}

export interface PreviewPayload {
  preview_key: string;
  caption_style?: CaptionStyle;
}

export interface MotionPayload {
  shots: Shot[];
  estimate: { model: string; clips: number; total_seconds: number };
}

export interface ClipsPayload {
  shots: Shot[];
  clips: Record<string, string[]>;
  selected: Record<string, number>;
  errors: Record<string, string>;
  video_model?: string;
}

export interface FinalPayload {
  final_key: string;
  caption_style?: CaptionStyle;
}

export interface StageProps<P> {
  view: ProjectView;
  payload: P;
  send: (decision: Decision) => Promise<void>;
  pending: boolean;
  options: Options | null;
}
