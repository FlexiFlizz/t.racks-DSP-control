"use client";

import { cn } from "@/lib/utils";
import { Check } from "lucide-react";
import type { Preset } from "@/types/dsp";

interface PresetsSectionProps {
  presets: Preset[];
  onLoadPreset: (index: number) => void;
}

export function PresetsSection({ presets, onLoadPreset }: PresetsSectionProps) {
  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0c0c10] p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Presets</span>
        <span className="text-[9px] text-zinc-600">16 emplacements</span>
      </div>

      <div className="grid grid-cols-4 md:grid-cols-8 gap-2">
        {presets.map((preset) => (
          <button
            key={preset.index}
            onClick={() => onLoadPreset(preset.index)}
            className={cn(
              "relative flex flex-col items-center justify-center p-2 h-16 rounded-md border transition-all text-center",
              preset.active
                ? "bg-blue-500/10 border-blue-500/60 shadow-[0_0_12px_rgba(59,130,246,0.15)]"
                : "bg-zinc-900 border-zinc-800 hover:border-zinc-600",
            )}
          >
            {preset.active && (
              <Check className="absolute top-1 right-1 h-3 w-3 text-blue-400" />
            )}
            <span className="text-[9px] font-mono text-zinc-600">
              {String(preset.index + 1).padStart(2, "0")}
            </span>
            <span className={cn(
              "text-[10px] font-medium truncate w-full",
              preset.active ? "text-blue-300" : "text-zinc-400",
            )}>
              {preset.name}
            </span>
          </button>
        ))}
      </div>
    </div>
  );
}
