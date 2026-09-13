import { CheckCircle2, TriangleAlert } from "lucide-react";
import type { CriticReport, FactCheckReport } from "@/lib/types";

function Passed({ children }: { children: string }) {
  return (
    <div className="flex items-center gap-2 rounded-xl border border-ok/25 bg-ok/5 px-4 py-3 text-sm text-ok">
      <CheckCircle2 className="h-4 w-4 shrink-0" />
      {children}
    </div>
  );
}

function Issues({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-gold/30 bg-gold/5 px-4 py-3">
      <p className="mb-2 flex items-center gap-2 text-sm font-semibold text-gold">
        <TriangleAlert className="h-4 w-4" />
        {title}
      </p>
      <ul className="space-y-1.5 text-sm text-dim">{children}</ul>
    </div>
  );
}

export function FactCheckNote({ report }: { report: FactCheckReport | null | undefined }) {
  if (!report) return null;
  if (report.passed || report.issues.length === 0) {
    return <Passed>Fact check passed: every claim is supported by the fact sheet.</Passed>;
  }
  return (
    <Issues title={`Fact check: ${report.issues.length} unresolved`}>
      {report.issues.map((issue, i) => (
        <li key={i}>
          <span className="text-ink">{issue.location}</span>: “{issue.claim}” (
          {issue.problem.replace(/_/g, " ")}). <span className="text-faint">Fix: {issue.suggested_fix}</span>
        </li>
      ))}
    </Issues>
  );
}

export function CriticNote({ report, rounds }: { report: CriticReport | null; rounds: number }) {
  if (!report) return null;
  if (report.passed || report.issues.length === 0) {
    return (
      <Passed>
        {`Scene review passed after ${rounds} ${rounds === 1 ? "round" : "rounds"}: no anachronisms, continuity, or character-look problems.`}
      </Passed>
    );
  }
  return (
    <Issues title={`Scene review: ${report.issues.length} unresolved after ${rounds} rounds`}>
      {report.issues.map((issue, i) => (
        <li key={i}>
          <span className="text-ink">
            Scene {issue.scene_order} · {issue.category.replace(/_/g, " ")}
          </span>
          : {issue.detail} <span className="text-faint">Fix: {issue.suggested_fix}</span>
        </li>
      ))}
    </Issues>
  );
}
