"use client";

import { useCallback, useRef, useState } from "react";
import { cn } from "@/lib/utils";

interface RotaryKnobProps {
  value: number;
  min: number;
  max: number;
  onChange: (v: number) => void;
  label?: string;
  display?: string;
  size?: number;
  color?: string;
  logarithmic?: boolean;
  className?: string;
}

const ARC_START = 135; // degrees from top
const ARC_END = 405;   // 135 + 270
const ARC_RANGE = ARC_END - ARC_START;

export function RotaryKnob({
  value, min, max, onChange, label, display,
  size = 52, color = "#6366f1", logarithmic, className,
}: RotaryKnobProps) {
  const ref = useRef<HTMLDivElement>(null);
  const [dragging, setDragging] = useState(false);
  const startY = useRef(0);
  const startVal = useRef(value);

  // Value to normalized 0-1
  const normalize = (v: number) => {
    if (logarithmic) {
      const lMin = Math.log10(Math.max(0.001, min));
      const lMax = Math.log10(Math.max(0.001, max));
      return (Math.log10(Math.max(0.001, v)) - lMin) / (lMax - lMin);
    }
    return (v - min) / (max - min);
  };

  const denormalize = (n: number) => {
    if (logarithmic) {
      const lMin = Math.log10(Math.max(0.001, min));
      const lMax = Math.log10(Math.max(0.001, max));
      return Math.pow(10, lMin + n * (lMax - lMin));
    }
    return min + n * (max - min);
  };

  const norm = normalize(value);
  const angle = ARC_START + norm * ARC_RANGE;

  // Drag: vertical movement changes value
  const handlePointerDown = useCallback((e: React.PointerEvent) => {
    e.preventDefault();
    setDragging(true);
    startY.current = e.clientY;
    startVal.current = value;
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  }, [value]);

  const handlePointerMove = useCallback((e: React.PointerEvent) => {
    if (!dragging) return;
    const dy = startY.current - e.clientY;
    const sensitivity = e.shiftKey ? 600 : 150;
    const startNorm = normalize(startVal.current);
    const newNorm = Math.max(0, Math.min(1, startNorm + dy / sensitivity));
    onChange(denormalize(newNorm));
  }, [dragging, min, max, onChange, logarithmic]);

  const handlePointerUp = useCallback(() => setDragging(false), []);

  // Wheel support
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const step = e.shiftKey ? 0.002 : 0.01;
    const delta = e.deltaY > 0 ? -step : step;
    const newNorm = Math.max(0, Math.min(1, norm + delta));
    onChange(denormalize(newNorm));
  }, [norm, min, max, onChange, logarithmic]);

  // SVG arc for the track
  const r = (size - 8) / 2;
  const cx = size / 2;
  const cy = size / 2;

  const polarToCart = (deg: number, radius: number) => {
    const rad = ((deg - 90) * Math.PI) / 180;
    return { x: cx + radius * Math.cos(rad), y: cy + radius * Math.sin(rad) };
  };

  // Background arc (full track)
  const bgStart = polarToCart(ARC_START, r);
  const bgEnd = polarToCart(ARC_END, r);
  const bgArc = `M${bgStart.x},${bgStart.y} A${r},${r} 0 1 1 ${bgEnd.x},${bgEnd.y}`;

  // Value arc
  const valEnd = polarToCart(angle, r);
  const largeArc = angle - ARC_START > 180 ? 1 : 0;
  const valArc = `M${bgStart.x},${bgStart.y} A${r},${r} 0 ${largeArc} 1 ${valEnd.x},${valEnd.y}`;

  // Pointer line
  const pointerInner = polarToCart(angle, r * 0.35);
  const pointerOuter = polarToCart(angle, r * 0.75);

  return (
    <div className={cn("flex flex-col items-center gap-1", className)}>
      {label && (
        <span className="text-[8px] uppercase tracking-wider text-muted-foreground/60 font-medium">
          {label}
        </span>
      )}

      <div
        ref={ref}
        className={cn("relative cursor-ns-resize select-none", dragging && "cursor-grabbing")}
        style={{ width: size, height: size }}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        onWheel={handleWheel}
      >
        <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
          {/* Outer shadow ring */}
          <circle cx={cx} cy={cy} r={r + 1} fill="none" stroke="#000" strokeWidth={2} strokeOpacity={0.3} />

          {/* Knob body - dark metallic gradient */}
          <defs>
            <radialGradient id={`knob-${label}`} cx="40%" cy="35%">
              <stop offset="0%" stopColor="#3a3a42" />
              <stop offset="60%" stopColor="#222228" />
              <stop offset="100%" stopColor="#18181c" />
            </radialGradient>
          </defs>
          <circle cx={cx} cy={cy} r={r - 2} fill={`url(#knob-${label})`}
            stroke="#2a2a30" strokeWidth={1} />

          {/* Inner highlight ring */}
          <circle cx={cx} cy={cy} r={r - 3} fill="none" stroke="#fff" strokeWidth={0.3} strokeOpacity={0.06} />

          {/* Background track arc */}
          <path d={bgArc} fill="none" stroke="#2a2a30" strokeWidth={2.5} strokeLinecap="round" />

          {/* Value arc */}
          {norm > 0.005 && (
            <path d={valArc} fill="none" stroke={color} strokeWidth={2.5} strokeLinecap="round"
              style={{ filter: dragging ? `drop-shadow(0 0 3px ${color}80)` : "none" }} />
          )}

          {/* Pointer line */}
          <line x1={pointerInner.x} y1={pointerInner.y} x2={pointerOuter.x} y2={pointerOuter.y}
            stroke={dragging ? "#fff" : "#ccc"} strokeWidth={1.5} strokeLinecap="round" />
        </svg>
      </div>

      {display && (
        <span className="text-[10px] font-mono font-medium text-foreground/80 tabular-nums">
          {display}
        </span>
      )}
    </div>
  );
}
