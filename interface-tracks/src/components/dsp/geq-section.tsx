"use client";

import { useState, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { EditableValue } from "./editable-value";
import { cn, formatFreq } from "@/lib/utils";
import { DSP206_CONFIG, GEQ_FREQUENCIES } from "@/types/dsp";

interface GEQSectionProps {
  geqs: Record<string, number[]>;
  onBandChange: (channel: string, bandIndex: number, db: number) => void;
}

const SLIDER_H = 140;

function dbToSliderY(db: number): number {
  return ((12 - db) / 24) * SLIDER_H;
}

export function GEQSection({ geqs, onBandChange }: GEQSectionProps) {
  const [selectedChannel, setSelectedChannel] = useState(DSP206_CONFIG.inputs[0].name);
  const [draggingBand, setDraggingBand] = useState<number | null>(null);
  const bands = geqs[selectedChannel] || [];

  const handleSliderDrag = useCallback((bandIdx: number, e: React.PointerEvent<HTMLDivElement>) => {
    const rect = e.currentTarget.getBoundingClientRect();
    const y = e.clientY - rect.top;
    const db = 12 - (y / rect.height) * 24;
    const clamped = Math.max(-12, Math.min(12, Math.round(db * 10) / 10));
    onBandChange(selectedChannel, bandIdx, clamped);
  }, [selectedChannel, onBandChange]);

  return (
    <div className="space-y-3">
      {/* Input channel selector */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] text-zinc-500 uppercase tracking-wider">Canal :</span>
        {DSP206_CONFIG.inputs.map(ch => (
          <Button
            key={ch.name}
            variant={selectedChannel === ch.name ? "default" : "ghost"}
            size="sm"
            onClick={() => setSelectedChannel(ch.name)}
            className={cn(
              "h-7 px-2.5 text-xs",
              selectedChannel === ch.name && "bg-blue-600 hover:bg-blue-700",
            )}
          >
            {ch.name}
          </Button>
        ))}
        <div className="flex-1" />
        <Button
          variant="ghost"
          size="sm"
          className="h-7 px-2.5 text-xs text-zinc-400"
          onClick={() => GEQ_FREQUENCIES.forEach((_, i) => onBandChange(selectedChannel, i, 0))}
        >
          FLAT
        </Button>
      </div>

      {/* GEQ 31 bands */}
      <div className="rounded-lg border border-zinc-800 bg-[#0a0a12] p-3 pt-2 overflow-x-auto">
        {/* dB scale */}
        <div className="flex">
          <div className="w-7 flex-shrink-0" />
          <div className="flex-1 flex justify-between text-[7px] text-zinc-600 font-mono px-1 mb-1">
            <span>+12</span>
            <span>+6</span>
            <span>0</span>
            <span>-6</span>
            <span>-12</span>
          </div>
        </div>

        <div className="flex gap-[3px]">
          {/* dB scale side */}
          <div className="flex-shrink-0 w-7 relative" style={{ height: SLIDER_H }}>
            {[-12, -6, 0, 6, 12].map(db => (
              <div key={db} className="absolute right-0 flex items-center" style={{ top: dbToSliderY(db) }}>
                <span className="text-[7px] text-zinc-600 font-mono pr-1">
                  {db > 0 ? `+${db}` : db}
                </span>
              </div>
            ))}
          </div>

          {GEQ_FREQUENCIES.map((freq, i) => {
            const db = bands[i] || 0;
            const y = dbToSliderY(db);
            const zeroY = dbToSliderY(0);

            return (
              <div key={i} className="flex flex-col items-center" style={{ width: 24 }}>
                {/* Slider track */}
                <div
                  className="relative bg-zinc-900 rounded-sm cursor-pointer"
                  style={{ width: 18, height: SLIDER_H }}
                  onPointerDown={(e) => {
                    setDraggingBand(i);
                    (e.target as HTMLElement).setPointerCapture(e.pointerId);
                    handleSliderDrag(i, e);
                  }}
                  onPointerMove={(e) => draggingBand === i && handleSliderDrag(i, e)}
                  onPointerUp={() => setDraggingBand(null)}
                >
                  {/* Zero line */}
                  <div className="absolute left-0 right-0 h-px bg-zinc-700" style={{ top: zeroY }} />

                  {/* Fill bar */}
                  {db !== 0 && (
                    <div
                      className="absolute left-1 right-1 rounded-[1px]"
                      style={{
                        top: db > 0 ? y : zeroY,
                        height: Math.abs(y - zeroY),
                        backgroundColor: db > 0
                          ? `rgba(239, 68, 68, ${Math.min(1, Math.abs(db) / 8)})`
                          : `rgba(34, 197, 94, ${Math.min(1, Math.abs(db) / 8)})`,
                      }}
                    />
                  )}

                  {/* Knob */}
                  <div
                    className={cn(
                      "absolute left-0 right-0 h-[6px] rounded-[2px] transition-colors",
                      db !== 0 ? "bg-zinc-200" : "bg-zinc-600",
                      draggingBand === i && "bg-white",
                    )}
                    style={{ top: y - 3 }}
                  />
                </div>

                {/* Value */}
                <EditableValue
                  value={db}
                  onChange={(v) => onBandChange(selectedChannel, i, v)}
                  min={-12} max={12} step={0.1} precision={1}
                  className={cn(
                    "text-[7px] mt-0.5 h-3",
                    db > 0 && "text-red-400",
                    db < 0 && "text-green-400",
                    db === 0 && "text-zinc-700",
                  )}
                  formatFn={(v) => v === 0 ? "" : (v > 0 ? `+${v.toFixed(1)}` : v.toFixed(1))}
                />

                {/* Freq label */}
                <span className={cn(
                  "text-[7px] font-mono mt-0.5",
                  [0, 5, 10, 15, 20, 25, 30].includes(i) ? "text-zinc-400" : "text-zinc-700",
                )}>
                  {freq >= 1000 ? `${freq / 1000}k` : freq}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
