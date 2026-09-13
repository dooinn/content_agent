import { FolderOpen, Landmark, PlusCircle, ShieldCheck } from "lucide-react";
import Link from "next/link";
import type { ReactNode } from "react";

export function Logo() {
  return (
    <Link href="/" className="flex items-center gap-3">
      <span className="flex h-9 w-9 items-center justify-center rounded-lg border border-gold/40 bg-gold/10 text-gold">
        <Landmark className="h-5 w-5" />
      </span>
      <span>
        <span className="block text-sm font-semibold text-ink">History Shorts Agent</span>
        <span className="block text-xs text-faint">Producer console</span>
      </span>
    </Link>
  );
}

function Sidebar({ children, width }: { children: ReactNode; width: string }) {
  return (
    <aside
      className={`sticky top-0 hidden h-screen ${width} shrink-0 flex-col overflow-y-auto border-r border-line bg-surface/40 px-4 py-6 lg:flex`}
    >
      <Logo />
      {children}
    </aside>
  );
}

export function HomeShell({ children }: { children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar width="w-64">
        <nav className="mt-8 space-y-1 text-sm">
          <Link
            href="/"
            className="flex items-center gap-3 rounded-lg border border-gold/30 bg-gold/10 px-3 py-2 font-medium text-gold"
          >
            <FolderOpen className="h-4 w-4" />
            Projects
          </Link>
          <a
            href="#new-short"
            className="flex items-center gap-3 rounded-lg px-3 py-2 text-dim hover:bg-raised hover:text-ink"
          >
            <PlusCircle className="h-4 w-4" />
            New short
          </a>
        </nav>
        <div className="mt-auto rounded-xl border border-line bg-surface p-4 text-xs leading-relaxed text-faint">
          <ShieldCheck className="mb-2 h-4 w-4 text-gold" />
          Nothing paid runs without your approval. Coin icons mark steps that call image, audio,
          or video models.
        </div>
      </Sidebar>
      <main className="min-w-0 flex-1 px-4 py-6 sm:px-8 sm:py-8">
        <div className="mb-6 lg:hidden">
          <Logo />
        </div>
        {children}
      </main>
    </div>
  );
}

export function ProjectShell({ sidebar, children }: { sidebar: ReactNode; children: ReactNode }) {
  return (
    <div className="flex min-h-screen">
      <Sidebar width="w-72">
        <div className="mt-8">{sidebar}</div>
      </Sidebar>
      <main className="min-w-0 flex-1 px-4 pt-6 sm:px-8 sm:pt-8">{children}</main>
    </div>
  );
}
