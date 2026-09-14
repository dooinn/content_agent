import type { Options } from "@/lib/types";
import { Segmented } from "./ui";

/** Target video length. Longer videos mean more scenes, so more images and clips to pay for. */
export function LengthPicker({
  options,
  value,
  onChange,
}: {
  options: Options;
  value: number;
  onChange: (seconds: number) => void;
}) {
  const current = options.durations.find((duration) => duration.seconds === value);
  const shortest = options.durations[0];
  return (
    <div>
      <Segmented
        value={String(value)}
        options={options.durations.map((duration) => ({ id: String(duration.seconds), label: duration.label }))}
        onChange={(id) => onChange(Number(id))}
      />
      {current && (
        <p className="mt-1.5 text-xs text-faint">
          {current.note}
          {shortest && current.seconds > shortest.seconds && " · image and video cost grows with the scene count"}
        </p>
      )}
    </div>
  );
}
