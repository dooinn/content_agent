import { CheckCircle2, Download, Film } from "lucide-react";
import { Card, SectionTitle } from "@/components/ui";
import { assetUrl, videoUrl } from "@/lib/api";
import type { ProjectView } from "@/lib/types";

const linkClass =
  "inline-flex items-center gap-2 rounded-lg border border-line-strong bg-surface px-4 py-2 text-sm font-semibold text-ink hover:bg-raised";

/** A finished project, or one that stopped at the animatic. */
export function FinalView({ view }: { view: ProjectView }) {
  const final = assetUrl(view, view.state.final_key);
  const animatic = assetUrl(view, view.state.preview_key);
  const video = videoUrl(view, view.state.final_key ?? view.state.preview_key);

  return (
    <div className="grid gap-6 xl:grid-cols-[minmax(0,22rem)_1fr]">
      <Card className="p-3">
        {video ? (
          <video controls preload="metadata" src={video} className="aspect-[9/16] w-full rounded-lg bg-black" />
        ) : (
          <p className="text-sm text-faint">No video yet.</p>
        )}
      </Card>
      <Card className="h-fit space-y-4">
        <SectionTitle>{final ? "Final cut" : "Animatic"}</SectionTitle>
        <p className="flex items-center gap-2 text-sm text-dim">
          <CheckCircle2 className="h-4 w-4 text-ok" />
          {final
            ? "Kling clips cut to the narration, with burned-in captions and the music ducked under the voice."
            : "This project stopped at the animatic."}
        </p>
        <div className="flex flex-wrap gap-2">
          {final && (
            <a href={final} download className={linkClass}>
              <Download className="h-4 w-4" />
              Download MP4
            </a>
          )}
          {final && animatic && (
            <a href={animatic} target="_blank" rel="noreferrer" className={linkClass}>
              <Film className="h-4 w-4" />
              Open animatic
            </a>
          )}
        </div>
      </Card>
    </div>
  );
}
