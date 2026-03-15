"use client";

import { useCallback, useRef, useState } from "react";
import { cn, formatGain } from "@/lib/utils";
import { EditableValue, EditableLabel } from "./editable-value";
import { StereoMeter } from "./meter";
import { DSP206_CONFIG } from "@/types/dsp";
import type { ChannelState } from "@/types/dsp";

interface GainPageProps {
  channels: Record<string, ChannelState>;
  onGainChange: (ch: string, db: number) => void;
  onMuteToggle: (ch: string) => void;
  onPhaseToggle: (ch: string) => void;
  onLabelChange: (ch: string, label: string) => void;
}

const COLORS = ["#06b6d4", "#06b6d4", "#ef4444", "#22c55e", "#eab308", "#a855f7", "#f97316", "#3b82f6"];

export function GainPage({ channels, onGainChange, onMuteToggle, onPhaseToggle, onLabelChange }: GainPageProps) {
  const all = [...DSP206_CONFIG.inputs, ...DSP206_CONFIG.outputs];
  return (
    <div className="flex gap-2 items-stretch justify-center h-full">
      {all.map((ch, i) => {
        const isSep = i === DSP206_CONFIG.inputs.length;
        return (
          <div key={ch.name} className="flex items-stretch">
            {isSep && <div className="w-px bg-border mx-2 self-stretch" />}
            <FaderStrip name={ch.name} state={channels[ch.name]} color={COLORS[i]}
              onGain={db => onGainChange(ch.name, db)}
              onMute={() => onMuteToggle(ch.name)}
              onPhase={() => onPhaseToggle(ch.name)}
              onLabel={l => onLabelChange(ch.name, l)} />
          </div>
        );
      })}
    </div>
  );
}

// ── dB scale marks for the fader ──
const DB_MARKS = [12, 6, 0, -6, -12, -20, -30, -40, -60];

function FaderStrip({ name, state, color, onGain, onMute, onPhase, onLabel }: {
  name: string; state: ChannelState; color: string;
  onGain: (db: number) => void; onMute: () => void; onPhase: () => void; onLabel: (l: string) => void;
}) {
  const trackRef = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);

  const pct = ((state.gain + 60) / 72) * 100;
  const simL = state.mute ? 0 : Math.max(0, Math.min(96, pct * 0.7 + 10 + Math.random() * 6));
  const simR = state.mute ? 0 : Math.max(0, Math.min(96, pct * 0.68 + 8 + Math.random() * 6));

  const handleDrag = useCallback((e: React.PointerEvent) => {
    if (!trackRef.current) return;
    const rect = trackRef.current.getBoundingClientRect();
    const p = 1 - (e.clientY - rect.top) / rect.height;
    const db = Math.max(-60, Math.min(12, p * 72 - 60));
    onGain(db >= -20 ? Math.round(db * 10) / 10 : Math.round(db * 2) / 2);
  }, [onGain]);

  return (
    <div className={cn(
      "flex flex-col items-center w-[82px] rounded-xl p-2 gap-2 transition-opacity",
      "bg-gradient-to-b from-[#131318] to-[#0e0e12] border border-[#1e1e28]",
      "shadow-[inset_0_1px_0_rgba(255,255,255,0.03)]",
      state.mute && "opacity-40",
    )}>
      {/* Channel name */}
      <EditableLabel value={state.label || name} onChange={onLabel}
        className="text-[10px] font-semibold w-full text-center truncate text-muted-foreground" />

      {/* Gain readout */}
      <div className="text-center">
        <EditableValue value={state.gain} onChange={onGain} min={-60} max={12} step={0.1} precision={1}
          formatFn={v => formatGain(v)}
          className={cn("text-sm font-bold font-mono",
            state.gain > 0 && "text-red-400",
            state.gain === 0 && "text-emerald-400",
            state.gain < 0 && state.gain > -20 && "text-foreground",
            state.gain <= -20 && "text-muted-foreground")} />
        <div className="text-[7px] text-muted-foreground/50 mt-0.5">dB</div>
      </div>

      {/* Fader + Meters */}
      <div className="flex gap-1.5 h-[200px] w-full">
        {/* dB scale */}
        <div className="flex flex-col justify-between text-[6px] font-mono text-muted-foreground/30 w-5 text-right py-1">
          {DB_MARKS.map(db => (
            <span key={db} className={cn(db === 0 && "text-muted-foreground/60")}>{db}</span>
          ))}
        </div>

        {/* Fader track */}
        <div ref={trackRef} className="w-4 relative cursor-ns-resize rounded-sm overflow-hidden bg-[#0a0a0e]"
          onPointerDown={e => {
            setDragging(true);
            (e.target as HTMLElement).setPointerCapture(e.pointerId);
            handleDrag(e);
          }}
          onPointerMove={e => dragging && handleDrag(e)}
          onPointerUp={() => setDragging(false)}>

          {/* Track groove */}
          <div className="absolute inset-x-[6px] inset-y-0 bg-[#151518] rounded-full" />

          {/* dB marks on track */}
          {DB_MARKS.map(db => {
            const y = (1 - (db + 60) / 72) * 100;
            return <div key={db} className="absolute left-0 right-0 h-px" style={{ top: `${y}%` }}>
              <div className={cn("h-px mx-0.5", db === 0 ? "bg-white/15" : "bg-white/5")} />
            </div>;
          })}

          {/* Fader thumb - metallic cap style */}
          <div className="absolute left-0 right-0 flex flex-col items-center transition-[bottom] duration-[30ms]"
            style={{ bottom: `calc(${pct}% - 10px)` }}>
            <div className="w-3.5 h-[20px] rounded-[3px] shadow-lg"
              style={{
                background: dragging
                  ? `linear-gradient(180deg, ${color}ee, ${color}aa)`
                  : "linear-gradient(180deg, #555 0%, #333 40%, #444 60%, #2a2a2a 100%)",
                boxShadow: dragging
                  ? `0 0 10px ${color}60, inset 0 1px 0 rgba(255,255,255,0.2)`
                  : "0 2px 4px rgba(0,0,0,0.5), inset 0 1px 0 rgba(255,255,255,0.1)",
              }}>
              {/* Grip lines */}
              <div className="flex flex-col items-center justify-center h-full gap-[2px] py-1">
                <div className="w-2 h-px bg-white/20" />
                <div className="w-2 h-px bg-white/20" />
                <div className="w-2 h-px bg-white/20" />
              </div>
            </div>
          </div>
        </div>

        {/* LED meters */}
        <StereoMeter left={simL} right={simR} className="w-5 h-full" />
      </div>

      {/* Phase button */}
      <button onClick={onPhase}
        className={cn(
          "w-full h-5 rounded-md text-[9px] font-bold transition-all",
          state.phase
            ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500/30 shadow-[0_0_6px_rgba(234,179,8,0.2)]"
            : "bg-[#141418] text-muted-foreground/25 border border-[#1e1e28] hover:text-muted-foreground/50",
        )}>
        {"\u00D8"}
      </button>

      {/* Mute button (CUE-style glowing) */}
      <button onClick={onMute}
        className={cn(
          "w-full h-7 rounded-md text-[10px] font-bold uppercase tracking-wider transition-all",
          state.mute
            ? "bg-red-500/90 text-white shadow-[0_0_14px_rgba(239,68,68,0.4),inset_0_1px_0_rgba(255,255,255,0.15)]"
            : "bg-[#141418] text-muted-foreground/25 border border-[#1e1e28] hover:text-muted-foreground/50",
        )}>
        MUTE
      </button>

      {/* Color indicator */}
      <div className="w-full h-1 rounded-full shadow-sm"
        style={{ backgroundColor: color, opacity: 0.6, boxShadow: `0 0 6px ${color}30` }} />
    </div>
  );
}
