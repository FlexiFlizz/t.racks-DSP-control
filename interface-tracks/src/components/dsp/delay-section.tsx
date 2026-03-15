"use client";

import { EditableValue } from "./editable-value";
import { DSP206_CONFIG } from "@/types/dsp";
import { cn } from "@/lib/utils";
import { useCallback, useState } from "react";

interface DelaySectionProps {
  delays: Record<string, number>;
  onDelayChange: (channel: string, ms: number) => void;
}

const SPEED_OF_SOUND = 343.0; // m/s at ~20C
const MAX_DELAY = 300; // ms
const BAR_W = 600;

export function DelaySection({ delays, onDelayChange }: DelaySectionProps) {
  const [dragging, setDragging] = useState<string | null>(null);

  const handleBarDrag = useCallback((channel: string, e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const ms = Math.max(0, Math.min(MAX_DELAY, (x / rect.width) * MAX_DELAY));
    onDelayChange(channel, Math.round(ms * 10) / 10);
  }, [onDelayChange]);

  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0c0c10] p-4 space-y-1">
      <div className="flex items-center gap-2 mb-3">
        <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Delay</span>
        <span className="text-[9px] text-zinc-600">Sorties uniquement</span>
        <span className="text-[8px] text-yellow-600 ml-auto">(experimental)</span>
      </div>

      {/* Scale */}
      <div className="flex items-center gap-3 mb-1">
        <div className="w-16" />
        <div className="flex-1 max-w-[600px]">
          <div className="flex justify-between text-[7px] text-zinc-600 font-mono px-0.5">
            {[0, 50, 100, 150, 200, 250, 300].map(ms => (
              <span key={ms}>{ms}</span>
            ))}
          </div>
        </div>
        <div className="w-20" />
        <div className="w-16" />
      </div>

      {DSP206_CONFIG.outputs.map(ch => {
        const ms = delays[ch.name] || 0;
        const metres = (ms / 1000) * SPEED_OF_SOUND;
        const pct = (ms / MAX_DELAY) * 100;

        return (
          <div key={ch.name} className="flex items-center gap-3 py-1.5 group">
            {/* Channel name */}
            <span className="w-16 text-[10px] font-bold text-amber-400 text-right">{ch.name}</span>

            {/* Delay bar */}
            <div
              className="flex-1 max-w-[600px] h-6 bg-zinc-900 rounded-sm relative cursor-pointer"
              onPointerDown={(e) => {
                setDragging(ch.name);
                (e.target as HTMLElement).setPointerCapture(e.pointerId);
                handleBarDrag(ch.name, e);
              }}
              onPointerMove={(e) => dragging === ch.name && handleBarDrag(ch.name, e)}
              onPointerUp={() => setDragging(null)}
            >
              {/* Fill */}
              <div
                className="absolute inset-y-0 left-0 rounded-sm bg-amber-500/20 transition-[width] duration-75"
                style={{ width: `${pct}%` }}
              />
              {/* Knob */}
              <div
                className={cn(
                  "absolute top-0 bottom-0 w-[3px] rounded-full transition-colors",
                  dragging === ch.name ? "bg-white" : "bg-amber-400",
                )}
                style={{ left: `calc(${pct}% - 1.5px)` }}
              />
              {/* Grid marks */}
              {[50, 100, 150, 200, 250].map(mark => (
                <div key={mark} className="absolute top-0 bottom-0 w-px bg-zinc-800"
                  style={{ left: `${(mark / MAX_DELAY) * 100}%` }} />
              ))}
            </div>

            {/* ms value */}
            <div className="w-20 flex items-center justify-end">
              <EditableValue
                value={ms}
                onChange={(v) => onDelayChange(ch.name, v)}
                min={0} max={MAX_DELAY} step={0.1} precision={1}
                suffix=" ms"
                className="text-[11px]"
              />
            </div>

            {/* metres value */}
            <span className="w-16 text-[10px] text-zinc-500 font-mono tabular-nums text-right">
              {metres.toFixed(2)} m
            </span>
          </div>
        );
      })}
    </div>
  );
}
