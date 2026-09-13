import type { ButtonHTMLAttributes, ReactNode } from "react";

export type Tone = "zinc" | "green" | "amber" | "red" | "blue";

const toneStyles: Record<Tone, string> = {
  zinc: "border-line-strong bg-raised text-dim",
  green: "border-ok/30 bg-ok/10 text-ok",
  amber: "border-gold/40 bg-gold/10 text-gold",
  red: "border-danger/30 bg-danger/10 text-danger",
  blue: "border-info/30 bg-info/10 text-info",
};

export function Badge({ tone = "zinc", children }: { tone?: Tone; children: ReactNode }) {
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium ${toneStyles[tone]}`}
    >
      {children}
    </span>
  );
}

const buttonStyles = {
  primary: "bg-gold text-canvas hover:bg-gold-strong",
  secondary: "border border-line-strong bg-surface text-ink hover:bg-raised",
  ghost: "text-dim hover:bg-raised hover:text-ink",
  danger: "bg-danger text-canvas hover:bg-danger/90",
};

export function Button({
  variant = "primary",
  className = "",
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { variant?: keyof typeof buttonStyles }) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-gold disabled:cursor-not-allowed disabled:opacity-40 ${buttonStyles[variant]} ${className}`}
      {...props}
    />
  );
}

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <section className={`rounded-xl border border-line bg-surface p-5 ${className}`}>
      {children}
    </section>
  );
}

export function SectionTitle({ children }: { children: ReactNode }) {
  return (
    <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-faint">{children}</h3>
  );
}

export function Detail({ label, children }: { label: string; children: ReactNode }) {
  return (
    <div>
      <p className="text-xs font-semibold uppercase tracking-wider text-faint">{label}</p>
      <div className="mt-1.5 text-sm leading-relaxed text-dim">{children}</div>
    </div>
  );
}

export const inputClass =
  "w-full rounded-lg border border-line-strong bg-canvas px-3 py-2 text-sm text-ink placeholder:text-faint focus:border-gold/70 focus:outline-none";

export const fileInputClass =
  "block text-sm text-dim file:mr-3 file:cursor-pointer file:rounded-lg file:border file:border-line-strong file:bg-raised file:px-3 file:py-1.5 file:text-sm file:font-medium file:text-ink hover:file:bg-line";

export function FeedbackField({
  value,
  onChange,
  hint,
}: {
  value: string;
  onChange: (value: string) => void;
  hint: string;
}) {
  return (
    <label className="block">
      <span className="text-sm font-medium text-ink">Direction</span>
      <span className="block text-xs text-faint">{hint}</span>
      <textarea
        value={value}
        onChange={(event) => onChange(event.target.value)}
        rows={3}
        placeholder="Optional"
        className={`mt-2 ${inputClass}`}
      />
    </label>
  );
}

/** Single-line direction input for the sticky action bar. */
export function DirectionInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder: string;
}) {
  return (
    <label className="flex min-w-64 flex-1 flex-col gap-1">
      <span className="text-xs text-faint">Direction (optional)</span>
      <input
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className={inputClass}
      />
    </label>
  );
}

export function Checkbox({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-dim">
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
        className="h-4 w-4 accent-gold"
      />
      {label}
    </label>
  );
}

export function Toggle({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="inline-flex items-center gap-2.5 text-sm text-dim hover:text-ink"
    >
      {label}
      <span
        className={`relative h-5 w-9 rounded-full transition ${checked ? "bg-gold" : "bg-line-strong"}`}
      >
        <span
          className={`absolute top-0.5 h-4 w-4 rounded-full bg-ink transition-all ${checked ? "left-4.5" : "left-0.5"}`}
        />
      </span>
    </button>
  );
}

export function Segmented<T extends string>({
  value,
  options,
  onChange,
}: {
  value: T;
  options: { id: T; label: string }[];
  onChange: (value: T) => void;
}) {
  return (
    <div className="inline-flex rounded-lg border border-line-strong bg-canvas p-0.5">
      {options.map((option) => (
        <button
          key={option.id}
          type="button"
          onClick={() => onChange(option.id)}
          className={`rounded-md px-3 py-1.5 text-xs font-medium transition ${
            value === option.id ? "bg-raised text-ink shadow" : "text-faint hover:text-dim"
          }`}
        >
          {option.label}
        </button>
      ))}
    </div>
  );
}

export function Stat({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div>
      <p className="text-xs text-faint">{label}</p>
      <p className="text-lg font-semibold text-ink">{value}</p>
    </div>
  );
}

export function ErrorNote({ children }: { children: ReactNode }) {
  return (
    <p role="alert" className="rounded-lg border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger">
      {children}
    </p>
  );
}

/** Add or remove a value from a list, for checkbox groups. */
export function toggle<T>(list: T[], value: T, on: boolean): T[] {
  return on ? [...list.filter((item) => item !== value), value] : list.filter((item) => item !== value);
}
