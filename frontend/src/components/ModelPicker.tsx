import type { ModelOption } from "@/lib/types";
import { Segmented } from "./ui";

export function ModelPicker({
  label,
  models,
  value,
  onChange,
}: {
  label: string;
  models: ModelOption[];
  value: string;
  onChange: (id: string) => void;
}) {
  return (
    <fieldset>
      <legend className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">{label}</legend>
      <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-3">
        {models.map((model) => {
          const selected = model.id === value;
          return (
            <label
              key={model.id}
              className={`cursor-pointer rounded-lg border px-3 py-2.5 transition ${
                selected ? "border-gold/60 bg-gold/10" : "border-line-strong bg-canvas hover:border-line-strong/80 hover:bg-raised"
              }`}
            >
              <input
                type="radio"
                name={label}
                value={model.id}
                checked={selected}
                onChange={() => onChange(model.id)}
                className="sr-only"
              />
              <span className={`block text-sm font-medium ${selected ? "text-gold" : "text-ink"}`}>
                {model.label}
              </span>
              <span className="block text-xs text-faint">{model.note}</span>
            </label>
          );
        })}
      </div>
    </fieldset>
  );
}

export function QualityPicker({
  qualities,
  value,
  onChange,
}: {
  qualities: string[];
  value: string;
  onChange: (quality: string) => void;
}) {
  return (
    <div>
      <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">Image quality</p>
      <Segmented
        value={value}
        options={qualities.map((quality) => ({ id: quality, label: quality[0].toUpperCase() + quality.slice(1) }))}
        onChange={onChange}
      />
    </div>
  );
}
