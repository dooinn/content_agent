"use client";

import type { CSSProperties } from "react";
import type { CaptionStyle, Options } from "@/lib/types";
import { Segmented, Toggle } from "./ui";

// Must match the families loaded in app/layout.tsx and bundled with the renderer.
const FONT_FAMILY: Record<string, string> = {
  montserrat: "var(--font-cap-montserrat)",
  inter: "var(--font-cap-inter)",
  "bebas-neue": "var(--font-cap-bebas)",
  cinzel: "var(--font-cap-cinzel)",
  playfair: "var(--font-cap-playfair)",
};
const FONT_WEIGHT: Record<string, number> = {
  montserrat: 800,
  inter: 700,
  "bebas-neue": 400,
  cinzel: 700,
  playfair: 700,
};

// Renderer layout on a 1920px-tall frame: caption baseline offsets from the bottom.
const FRAME_HEIGHT = 1920;
const BOTTOM_MARGIN: Record<string, number> = { bottom: 260, "lower-third": 520 };

export function captionCss(style: CaptionStyle): CSSProperties {
  return {
    fontFamily: FONT_FAMILY[style.font],
    fontWeight: FONT_WEIGHT[style.font] ?? 700,
    textTransform: style.uppercase ? "uppercase" : "none",
  };
}

/** A 9:16 frame with the caption drawn at the same relative size and position as the render. */
export function CaptionPreview({
  style,
  image,
  text = "At fourteen, he stepped on stage",
  className = "",
}: {
  style: CaptionStyle;
  image?: string;
  text?: string;
  className?: string;
}) {
  const vertical: CSSProperties =
    style.position === "center"
      ? { top: "50%", transform: "translateY(-50%)" }
      : { bottom: `${(BOTTOM_MARGIN[style.position] / FRAME_HEIGHT) * 100}%` };

  return (
    <div
      className={`relative aspect-[9/16] w-full overflow-hidden rounded-lg bg-black ${className}`}
      style={{ containerType: "size" }}
    >
      {image && <img src={image} alt="" className="absolute inset-0 h-full w-full object-cover" />}
      <p
        className="absolute inset-x-[7.4%] text-center leading-tight text-white"
        style={{
          ...vertical,
          ...captionCss(style),
          fontSize: `${(style.size / FRAME_HEIGHT) * 100}cqh`,
          WebkitTextStroke: "0.08em black",
          paintOrder: "stroke fill",
          textShadow: "0 0.05em 0.1em rgba(0,0,0,0.6)",
        }}
      >
        {text}
      </p>
    </div>
  );
}

export function CaptionStyleEditor({
  value,
  onChange,
  options,
  previewImage,
}: {
  value: CaptionStyle;
  onChange: (style: CaptionStyle) => void;
  options: Options;
  previewImage?: string;
}) {
  const set = (patch: Partial<CaptionStyle>) => onChange({ ...value, ...patch });

  return (
    <div className="grid gap-6 md:grid-cols-[minmax(0,12rem)_1fr]">
      <CaptionPreview style={value} image={previewImage} className="max-w-48" />
      <div className="space-y-5">
        <div>
          <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">Font</p>
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {options.caption_fonts.map((font) => {
              const selected = font.id === value.font;
              return (
                <button
                  key={font.id}
                  type="button"
                  onClick={() => set({ font: font.id })}
                  className={`rounded-lg border px-3 py-2 text-left transition ${
                    selected ? "border-gold/60 bg-gold/10" : "border-line-strong bg-canvas hover:bg-raised"
                  }`}
                >
                  <span
                    className="block truncate text-lg text-ink"
                    style={captionCss({ ...value, font: font.id })}
                  >
                    At fourteen
                  </span>
                  <span className={`block text-xs ${selected ? "text-gold" : "text-faint"}`}>{font.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        <label className="block">
          <span className="mb-2 flex items-center justify-between text-xs font-semibold uppercase tracking-wider text-faint">
            Size
            <span className="font-mono normal-case tracking-normal text-dim">{value.size}px</span>
          </span>
          <input
            type="range"
            min={options.caption_size.min}
            max={options.caption_size.max}
            step={2}
            value={value.size}
            onChange={(event) => set({ size: Number(event.target.value) })}
            className="w-full accent-gold"
          />
        </label>

        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wider text-faint">Position</p>
            <Segmented
              value={value.position}
              options={options.caption_positions}
              onChange={(position) => set({ position })}
            />
          </div>
          <Toggle label="All caps" checked={value.uppercase} onChange={(uppercase) => set({ uppercase })} />
        </div>
      </div>
    </div>
  );
}
