"use client";

import { Film, ImagePlus, Loader2, Plus, Search, SlidersHorizontal, Sparkles, X } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { type DragEvent, type FormEvent, useEffect, useState } from "react";
import { HomeShell } from "@/components/AppShell";
import { CaptionStyleEditor } from "@/components/CaptionStyleEditor";
import { ModelPicker, QualityPicker } from "@/components/ModelPicker";
import { StageProgress } from "@/components/PipelineStepper";
import { StatusBadge, stageLabel } from "@/components/StatusBadge";
import { Button, Card, ErrorNote, inputClass } from "@/components/ui";
import { createProject, errorMessage, listProjects, timeAgo, uploadImage } from "@/lib/api";
import type { CaptionStyle, ProjectSummary } from "@/lib/types";
import { useOptions } from "@/lib/useOptions";

const STEPS = [
  { title: "Research and story", text: "Sourced facts, a story angle, and a 30-second script." },
  { title: "Look and keyframes", text: "A visual bible, scene plans, and a keyframe per scene." },
  { title: "Video and final cut", text: "Animatic, video clips, captions, and music." },
];

export default function Home() {
  const router = useRouter();
  const options = useOptions();

  const [projects, setProjects] = useState<ProjectSummary[] | null>(null);
  const [now, setNow] = useState<number | null>(null);
  const [listError, setListError] = useState<string | null>(null);

  const [topic, setTopic] = useState("");
  const [styleFile, setStyleFile] = useState<File | null>(null);
  const [stylePreview, setStylePreview] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);
  const [voiceId, setVoiceId] = useState("");
  const [imageModel, setImageModel] = useState<string | null>(null);
  const [imageQuality, setImageQuality] = useState<string | null>(null);
  const [videoModel, setVideoModel] = useState<string | null>(null);
  const [captionStyle, setCaptionStyle] = useState<CaptionStyle | null>(null);
  const [creating, setCreating] = useState(false);
  const [createError, setCreateError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    const load = async () => {
      try {
        const list = await listProjects();
        if (active) {
          setProjects(list);
          setNow(Date.now());
          setListError(null);
        }
      } catch (err) {
        if (active) setListError(errorMessage(err));
      }
    };
    load();
    const timer = setInterval(load, 5000);
    return () => {
      active = false;
      clearInterval(timer);
    };
  }, []);

  const chooseStyle = (file: File | undefined) => {
    if (!file) return;
    if (stylePreview) URL.revokeObjectURL(stylePreview);
    setStyleFile(file);
    setStylePreview(URL.createObjectURL(file));
  };
  const clearStyle = () => {
    if (stylePreview) URL.revokeObjectURL(stylePreview);
    setStyleFile(null);
    setStylePreview(null);
  };
  const onDrop = (event: DragEvent<HTMLLabelElement>) => {
    event.preventDefault();
    setDragging(false);
    chooseStyle(event.dataTransfer.files?.[0]);
  };

  const create = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setCreating(true);
    setCreateError(null);
    try {
      const styleKey = styleFile ? (await uploadImage(styleFile)).key : undefined;
      const project = await createProject({
        topic: topic.trim(),
        styleRefKey: styleKey,
        voiceId: voiceId.trim() || undefined,
        imageModel: imageModel ?? undefined,
        imageQuality: imageQuality ?? undefined,
        videoModel: videoModel ?? undefined,
        captionStyle: captionStyle ?? undefined,
      });
      router.push(`/projects/${project.id}`);
    } catch (err) {
      setCreateError(errorMessage(err));
      setCreating(false);
    }
  };

  return (
    <HomeShell>
      <div className="mx-auto max-w-6xl space-y-8">
        <div className="flex items-center justify-between gap-4">
          <h1 className="text-3xl font-semibold tracking-tight">Projects</h1>
          <a
            href="#new-short"
            className="inline-flex items-center gap-2 rounded-lg bg-gold px-4 py-2 text-sm font-semibold text-canvas hover:bg-gold-strong"
          >
            <Plus className="h-4 w-4" />
            New short
          </a>
        </div>

        <section id="new-short" className="scroll-mt-8 overflow-hidden rounded-xl border border-line bg-surface">
          <form onSubmit={create} className="grid gap-6 p-6 lg:grid-cols-[0.9fr_1.1fr_1.2fr]">
            <div>
              <p className="flex items-center gap-2 text-lg font-semibold">
                <Sparkles className="h-5 w-5 text-gold" />
                Start a new short
              </p>
              <p className="mt-1.5 text-sm leading-relaxed text-dim">
                A 30-second vertical history video. You review and approve every step.
              </p>
            </div>

            <div className="space-y-3">
              <label className="block text-sm font-medium">
                Which historical figure?
                <span className="relative mt-2 block">
                  <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-faint" />
                  <input
                    required
                    minLength={2}
                    maxLength={200}
                    value={topic}
                    onChange={(event) => setTopic(event.target.value)}
                    placeholder="e.g. Louis XIV"
                    className={`${inputClass} py-2.5 pl-9 text-base`}
                  />
                </span>
              </label>
              <Button type="submit" className="w-full py-2.5" disabled={creating || topic.trim().length < 2}>
                {creating ? <Loader2 className="h-4 w-4 animate-spin" /> : <Sparkles className="h-4 w-4" />}
                {creating ? "Starting research…" : "Start research"}
              </Button>
              {createError && <ErrorNote>{createError}</ErrorNote>}
            </div>

            <div>
              <p className="text-sm font-medium">
                Style reference <span className="font-normal text-faint">(optional)</span>
              </p>
              <label
                onDragOver={(event) => {
                  event.preventDefault();
                  setDragging(true);
                }}
                onDragLeave={() => setDragging(false)}
                onDrop={onDrop}
                className={`mt-2 flex cursor-pointer items-center gap-4 rounded-lg border border-dashed p-3 transition ${
                  dragging ? "border-gold bg-gold/5" : "border-line-strong hover:border-gold/50"
                }`}
              >
                {stylePreview ? (
                  <img src={stylePreview} alt="Style reference" className="h-20 w-14 rounded-md object-cover" />
                ) : (
                  <span className="flex h-20 w-14 items-center justify-center rounded-md bg-raised text-faint">
                    <ImagePlus className="h-5 w-5" />
                  </span>
                )}
                <span className="min-w-0 flex-1 text-sm">
                  <span className="block truncate text-ink">{styleFile ? styleFile.name : "Drop an image here"}</span>
                  <span className="block text-xs text-faint">
                    {styleFile ? "Only its style is used" : "or click to browse · PNG, JPEG, WebP up to 10 MB"}
                  </span>
                </span>
                <input
                  type="file"
                  accept="image/png,image/jpeg,image/webp"
                  className="sr-only"
                  onChange={(event) => chooseStyle(event.target.files?.[0])}
                />
                {styleFile && (
                  <button
                    type="button"
                    onClick={(event) => {
                      event.preventDefault();
                      clearStyle();
                    }}
                    aria-label="Remove style reference"
                    className="rounded-md p-1 text-faint hover:bg-raised hover:text-ink"
                  >
                    <X className="h-4 w-4" />
                  </button>
                )}
              </label>
            </div>
          </form>

          <details className="group border-t border-line">
            <summary className="flex cursor-pointer list-none items-center gap-2 px-6 py-3 text-sm text-dim hover:text-ink">
              <SlidersHorizontal className="h-4 w-4" />
              Models, captions, and voice
              <span className="ml-auto text-xs text-faint group-open:hidden">Server defaults</span>
            </summary>
            {options ? (
              <div className="space-y-6 border-t border-line px-6 py-5">
                <div className="grid gap-6 xl:grid-cols-2">
                  <div className="space-y-4">
                    <ModelPicker
                      label="Image model"
                      models={options.image_models}
                      value={imageModel ?? options.defaults.image_model}
                      onChange={setImageModel}
                    />
                    <QualityPicker
                      qualities={options.image_qualities}
                      value={imageQuality ?? options.defaults.image_quality}
                      onChange={setImageQuality}
                    />
                  </div>
                  <ModelPicker
                    label="Video model"
                    models={options.video_models}
                    value={videoModel ?? options.defaults.video_model}
                    onChange={setVideoModel}
                  />
                </div>
                <div className="border-t border-line pt-5">
                  <p className="mb-3 text-xs font-semibold uppercase tracking-wider text-faint">Captions</p>
                  <CaptionStyleEditor
                    value={captionStyle ?? options.defaults.caption_style}
                    onChange={setCaptionStyle}
                    options={options}
                    previewImage={stylePreview ?? undefined}
                  />
                </div>
                <label className="block max-w-sm border-t border-line pt-5">
                  <span className="text-xs font-semibold uppercase tracking-wider text-faint">Narrator voice id</span>
                  <input
                    value={voiceId}
                    onChange={(event) => setVoiceId(event.target.value)}
                    placeholder="ElevenLabs voice id (server default if empty)"
                    className={`mt-2 ${inputClass}`}
                  />
                </label>
              </div>
            ) : (
              <p className="border-t border-line px-6 py-4 text-sm text-faint">Loading options…</p>
            )}
          </details>

          <ol className="grid gap-4 border-t border-line px-6 py-4 md:grid-cols-3">
            {STEPS.map((step, index) => (
              <li key={step.title} className="flex gap-3">
                <span
                  className={`flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-xs font-semibold ${
                    index === 0 ? "bg-gold text-canvas" : "border border-line-strong text-dim"
                  }`}
                >
                  {index + 1}
                </span>
                <span>
                  <span className="block text-sm font-medium">{step.title}</span>
                  <span className="block text-xs text-faint">{step.text}</span>
                </span>
              </li>
            ))}
          </ol>
        </section>

        <section>
          <div className="mb-4 flex items-center justify-between">
            <h2 className="text-lg font-semibold">Your projects</h2>
            {projects && <span className="text-sm text-faint">{projects.length} total</span>}
          </div>
          {listError && <ErrorNote>Could not load projects: {listError}</ErrorNote>}
          {projects === null && !listError && <p className="text-sm text-faint">Loading…</p>}
          {projects?.length === 0 && (
            <Card className="text-sm text-dim">No projects yet. Start one with a historical figure above.</Card>
          )}
          <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
            {projects?.map((project) => (
              <li key={project.id}>
                <Link
                  href={`/projects/${project.id}`}
                  className="flex h-full gap-4 rounded-xl border border-line bg-surface p-3 transition hover:border-line-strong hover:bg-raised"
                >
                  <div className="aspect-[9/16] w-24 shrink-0 overflow-hidden rounded-lg bg-raised">
                    {project.thumbnail_url ? (
                      <img src={project.thumbnail_url} alt="" className="h-full w-full object-cover" />
                    ) : (
                      <div className="flex h-full items-center justify-center text-faint">
                        <Film className="h-6 w-6" />
                      </div>
                    )}
                  </div>
                  <div className="flex min-w-0 flex-1 flex-col py-1 pr-1">
                    <p className="truncate text-lg font-semibold">{project.topic}</p>
                    <div className="mt-2">
                      <StatusBadge status={project.status} />
                    </div>
                    {project.status !== "done" && stageLabel(project.stage) && (
                      <p className="mt-2 text-xs text-dim">Current step: {stageLabel(project.stage)}</p>
                    )}
                    <div className="mt-auto pt-4">
                      <StageProgress stage={project.stage} status={project.status} />
                    </div>
                    <p className="mt-1 text-xs text-faint">{now ? `Updated ${timeAgo(project.updated_at, now)}` : ""}</p>
                  </div>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      </div>
    </HomeShell>
  );
}
