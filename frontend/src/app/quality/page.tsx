"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { HomeShell } from "@/components/AppShell";
import { BarList, type BarDatum } from "@/components/BarList";
import { StatusBadge } from "@/components/StatusBadge";
import { Card, ErrorNote, SectionTitle } from "@/components/ui";
import { errorMessage, getQuality } from "@/lib/api";
import { lengthLabel } from "@/lib/format";
import { STAGE_INFO } from "@/lib/stages";
import type { ProjectQuality, QualityReport } from "@/lib/types";

const percent = (value: number | null | undefined) =>
  value === null || value === undefined ? "–" : `${Math.round(value * 100)}%`;
const usd = (value: number | null | undefined) =>
  value === null || value === undefined ? "–" : `$${value.toFixed(2)}`;
const humanize = (text: string) => text.charAt(0).toUpperCase() + text.slice(1).replace(/_/g, " ");

function StatTile({ label, value, note }: { label: string; value: string; note: string }) {
  return (
    <Card>
      <p className="text-sm text-dim">{label}</p>
      <p className="mt-2 text-3xl font-semibold text-ink">{value}</p>
      <p className="mt-1.5 text-xs leading-relaxed text-faint">{note}</p>
    </Card>
  );
}

function TableToggle({ children }: { children: React.ReactNode }) {
  return (
    <details className="mt-4 border-t border-line pt-3 text-sm">
      <summary className="cursor-pointer text-xs text-faint hover:text-dim">Show as table</summary>
      <div className="mt-3 overflow-x-auto">{children}</div>
    </details>
  );
}

function factCheckCell(project: ProjectQuality) {
  const runs = Object.values(project.fact_check);
  const total = runs.reduce((sum, run) => sum + run.runs, 0);
  if (!total) return "–";
  const issues = runs.reduce((sum, run) => sum + run.first_draft_issues, 0);
  return `${issues} caught`;
}

export default function QualityPage() {
  const [report, setReport] = useState<QualityReport | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getQuality().then(setReport, (err) => setError(errorMessage(err)));
  }, []);

  const summary = report?.summary;
  const decisions = report?.projects.reduce((sum, p) => sum + p.reviews.decisions, 0) ?? 0;

  const stageBars: BarDatum[] =
    summary?.stages.map((stage) => ({
      key: stage.stage,
      label: STAGE_INFO[stage.stage]?.label ?? stage.stage,
      value: stage.first_try_rate ?? 0,
      display: percent(stage.first_try_rate),
      detail: `${stage.projects} ${stage.projects === 1 ? "project" : "projects"}, ${(stage.rework_per_project ?? 0).toFixed(1)} redos each`,
    })) ?? [];

  const categories = Object.entries(summary?.critic.categories ?? {});
  const categoryMax = Math.max(0, ...categories.map(([, count]) => count));
  const categoryBars: BarDatum[] = categories.map(([category, count]) => ({
    key: category,
    label: humanize(category),
    value: count,
    display: String(count),
    detail: `${count} ${count === 1 ? "issue" : "issues"} fixed before review`,
  }));

  return (
    <HomeShell active="quality">
      <div className="mx-auto max-w-6xl space-y-8">
        <header>
          <h1 className="text-3xl font-semibold tracking-tight">Quality</h1>
          <p className="mt-1.5 max-w-3xl text-sm text-dim">
            How often each stage passes review on the first try, what the fact checker and scene critic catch
            before a person sees the work, and what the model calls cost. Read back from the LangGraph checkpoints of
            every project.
          </p>
        </header>

        {error && <ErrorNote>Could not load metrics: {error}</ErrorNote>}
        {!report && !error && <p className="text-sm text-faint">Reading checkpoints…</p>}

        {summary && report && (
          <>
            <section className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4" aria-label="Headline metrics">
              <StatTile
                label="Approved on first review"
                value={percent(summary.first_try_rate)}
                note={`Share of stage reviews approved without a redo, over ${decisions} decisions in ${summary.projects} projects.`}
              />
              <StatTile
                label="Unsupported claims caught"
                value={String(summary.fact_check.issues_caught)}
                note={`By the fact checker before review. ${percent(summary.fact_check.clean_first_draft_rate)} of first drafts were clean.`}
              />
              <StatTile
                label="Scene problems caught"
                value={String(summary.critic.issues_found)}
                note={`By the critic before any image was generated, ${(summary.critic.issues_per_project ?? 0).toFixed(1)} per project.`}
              />
              <StatTile
                label="Claude cost per video"
                value={usd(summary.cost.claude_usd_per_project)}
                note={
                  summary.cost.tracked_projects
                    ? `Measured on ${summary.cost.tracked_projects} ${summary.cost.tracked_projects === 1 ? "project" : "projects"}; image, video, and voice use credits.`
                    : "Token usage is recorded for projects run from now on."
                }
              />
            </section>

            <section className="grid items-start gap-4 lg:grid-cols-2">
              <Card>
                <SectionTitle>First-try approval by stage</SectionTitle>
                <p className="-mt-1 mb-4 text-xs text-faint">Share of projects where the first decision was approve.</p>
                {stageBars.length ? (
                  <BarList data={stageBars} max={1} caption="First-try approval rate by stage" />
                ) : (
                  <p className="text-sm text-faint">No reviews yet.</p>
                )}
                <TableToggle>
                  <table className="w-full text-left text-xs">
                    <thead className="text-faint">
                      <tr>
                        <th className="py-1 font-medium">Stage</th>
                        <th className="py-1 text-right font-medium">Projects</th>
                        <th className="py-1 text-right font-medium">First try</th>
                        <th className="py-1 text-right font-medium">Redos per project</th>
                      </tr>
                    </thead>
                    <tbody className="tabular-nums text-dim">
                      {summary.stages.map((stage) => (
                        <tr key={stage.stage} className="border-t border-line">
                          <td className="py-1.5">{STAGE_INFO[stage.stage]?.label ?? stage.stage}</td>
                          <td className="py-1.5 text-right">{stage.projects}</td>
                          <td className="py-1.5 text-right">{percent(stage.first_try_rate)}</td>
                          <td className="py-1.5 text-right">{(stage.rework_per_project ?? 0).toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableToggle>
              </Card>

              <Card>
                <SectionTitle>What the scene critic catches</SectionTitle>
                <p className="-mt-1 mb-4 text-xs text-faint">
                  Issues flagged in scene drafts and rewritten before the producer reviewed them.
                </p>
                {categoryBars.length ? (
                  <BarList data={categoryBars} max={categoryMax} caption="Critic issues by category" />
                ) : (
                  <p className="text-sm text-faint">No critic issues recorded yet.</p>
                )}
                <TableToggle>
                  <table className="w-full text-left text-xs">
                    <thead className="text-faint">
                      <tr>
                        <th className="py-1 font-medium">Category</th>
                        <th className="py-1 text-right font-medium">Issues</th>
                      </tr>
                    </thead>
                    <tbody className="tabular-nums text-dim">
                      {categories.map(([category, count]) => (
                        <tr key={category} className="border-t border-line">
                          <td className="py-1.5">{humanize(category)}</td>
                          <td className="py-1.5 text-right">{count}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </TableToggle>
              </Card>
            </section>

            <section>
              <SectionTitle>Projects</SectionTitle>
              <div className="overflow-x-auto rounded-xl border border-line bg-surface">
                <table className="w-full min-w-[56rem] text-left text-sm">
                  <thead className="border-b border-line text-xs text-faint">
                    <tr>
                      <th className="px-4 py-3 font-medium">Project</th>
                      <th className="px-3 py-3 font-medium">Status</th>
                      <th className="px-3 py-3 text-right font-medium">Length</th>
                      <th className="px-3 py-3 text-right font-medium">Decisions</th>
                      <th className="px-3 py-3 text-right font-medium">Redos</th>
                      <th className="px-3 py-3 text-right font-medium">First try</th>
                      <th className="px-3 py-3 text-right font-medium">Fact check</th>
                      <th className="px-3 py-3 text-right font-medium">Critic</th>
                      <th className="px-3 py-3 text-right font-medium">Images</th>
                      <th className="px-3 py-3 text-right font-medium">Clip sec</th>
                      <th className="px-4 py-3 text-right font-medium">Claude</th>
                    </tr>
                  </thead>
                  <tbody className="tabular-nums">
                    {report.projects.map((project) => (
                      <tr key={project.project_id} className="border-t border-line text-dim">
                        <td className="px-4 py-3">
                          <Link href={`/projects/${project.project_id}`} className="font-medium text-ink hover:text-gold">
                            {project.topic}
                          </Link>
                          <span className="block font-mono text-[11px] text-faint">{project.project_id}</span>
                        </td>
                        <td className="px-3 py-3">
                          <StatusBadge status={project.status} />
                        </td>
                        <td className="px-3 py-3 text-right">{lengthLabel(project.target_seconds)}</td>
                        <td className="px-3 py-3 text-right">{project.reviews.decisions}</td>
                        <td className="px-3 py-3 text-right">{project.reviews.rework}</td>
                        <td className="px-3 py-3 text-right">{percent(project.reviews.first_try_rate)}</td>
                        <td className="px-3 py-3 text-right">{factCheckCell(project)}</td>
                        <td className="px-3 py-3 text-right">{project.critic ? project.critic.issues_found : "–"}</td>
                        <td className="px-3 py-3 text-right">{project.media.images}</td>
                        <td className="px-3 py-3 text-right">{project.media.clip_seconds}</td>
                        <td className="px-4 py-3 text-right">{usd(project.llm?.cost_usd)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
              <p className="mt-2 text-xs text-faint">
                Claude cost is measured from token usage recorded since this page was added; “–” marks older projects.
                Magnific and ElevenLabs bill in credits and characters, so they are counted as images and clip seconds.
              </p>
            </section>
          </>
        )}
      </div>
    </HomeShell>
  );
}
