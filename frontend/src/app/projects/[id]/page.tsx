"use client";

import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { use, useState } from "react";
import { ProjectShell } from "@/components/AppShell";
import { PipelineStepper, StageProgress } from "@/components/PipelineStepper";
import { StagePanel, WorkingNote } from "@/components/StagePanel";
import { StatusBadge } from "@/components/StatusBadge";
import { Button, Card, ErrorNote } from "@/components/ui";
import { decide, errorMessage, retryProject } from "@/lib/api";
import { lengthLabel } from "@/lib/format";
import { STAGE_INFO } from "@/lib/stages";
import type { Decision, Stage } from "@/lib/types";
import { useOptions } from "@/lib/useOptions";
import { useProject } from "@/lib/useProject";

export default function ProjectPage({ params }: PageProps<"/projects/[id]">) {
  const { id } = use(params);
  const { view, error, refresh } = useProject(id);
  const options = useOptions();
  const [pending, setPending] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  const run = async (action: () => Promise<unknown>) => {
    setPending(true);
    setActionError(null);
    try {
      await action();
      await refresh();
    } catch (err) {
      setActionError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };
  const send = (decision: Decision) => run(() => decide(id, decision));

  if (!view) {
    return (
      <div className="p-8">
        {error ? <ErrorNote>{error}</ErrorNote> : <p className="text-faint">Loading project…</p>}
      </div>
    );
  }

  const { project } = view;
  const busy = view.running || project.status === "running";
  const stage = view.stage ?? project.stage;
  const info = stage && stage in STAGE_INFO ? STAGE_INFO[stage as Stage] : null;
  const finished = !view.stage && !busy && (project.status === "done" || project.status === "final_ready");

  const title = busy ? "Working on the next step" : finished ? "Finished" : (info?.title ?? "Nothing to review");
  const helper = busy
    ? "Research and generation can take a few minutes. This page refreshes on its own."
    : finished
      ? "The final cut is ready to download."
      : (info?.helper ?? "");

  const sidebar = (
    <>
      <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-faint hover:text-ink">
        <ArrowLeft className="h-3.5 w-3.5" />
        All projects
      </Link>
      <h2 className="mt-3 text-xl font-semibold">{project.topic}</h2>
      <div className="mt-2">
        <StatusBadge status={project.status} />
      </div>
      <p className="mt-2 text-xs text-dim">Length: {lengthLabel(view.state.target_seconds)}</p>
      <p className="mt-1 font-mono text-[11px] text-faint">{project.id}</p>
      <div className="mt-6">
        <PipelineStepper stage={stage} status={project.status} running={busy} />
      </div>
    </>
  );

  return (
    <ProjectShell sidebar={sidebar}>
      <div className="mb-5 space-y-3 lg:hidden">
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs text-faint">
          <ArrowLeft className="h-3.5 w-3.5" />
          All projects
        </Link>
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-lg font-semibold">{project.topic}</span>
          <StatusBadge status={project.status} />
        </div>
        <StageProgress stage={stage} status={project.status} />
      </div>

      <header className="mb-6">
        <p className="hidden text-xs text-faint lg:block">
          <Link href="/" className="hover:text-ink">
            Projects
          </Link>{" "}
          / <span className="text-dim">{project.topic}</span>
        </p>
        <h1 className="mt-2 text-2xl font-semibold tracking-tight sm:text-3xl">{title}</h1>
        {helper && <p className="mt-1.5 text-sm text-dim">{helper}</p>}
      </header>

      <div className="space-y-4 pb-8">
        {error && <ErrorNote>Could not refresh: {error}</ErrorNote>}
        {actionError && <ErrorNote>{actionError}</ErrorNote>}

        {project.status === "failed" && (
          <Card className="flex flex-wrap items-center justify-between gap-3 border-danger/30 bg-danger/5">
            <p className="text-sm text-danger">{project.error}</p>
            <Button variant="danger" disabled={pending} onClick={() => run(() => retryProject(id))}>
              Retry from the last checkpoint
            </Button>
          </Card>
        )}

        {busy ? (
          <WorkingNote />
        ) : (
          <StagePanel
            key={`${view.stage}-${project.updated_at}`}
            view={view}
            send={send}
            pending={pending}
            options={options}
          />
        )}
      </div>
    </ProjectShell>
  );
}
