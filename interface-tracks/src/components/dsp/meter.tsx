"use client";

import { cn } from "@/lib/utils";

interface MeterProps {
  value: number; // 0-100
  className?: string;
  segments?: number;
}

// LED segmented meter (green -> yellow -> orange -> red)
export function Meter({ value, className, segments = 20 }: MeterProps) {
  const clamped = Math.max(0, Math.min(100, value));

  return (
    <div className={cn("flex flex-col-reverse gap-[2px]", className)}>
      {Array.from({ length: segments }, (_, i) => {
        const threshold = (i / segments) * 100;
        const active = clamped > threshold;
        const pct = i / segments;

        // Color gradient: green -> yellow -> orange -> red
        let color: string;
        let glow: string;
        if (pct > 0.9) { color = "#ef4444"; glow = "0 0 4px #ef444480"; }
        else if (pct > 0.8) { color = "#f97316"; glow = "0 0 4px #f9731660"; }
        else if (pct > 0.65) { color = "#f59e0b"; glow = "0 0 3px #f59e0b50"; }
        else if (pct > 0.5) { color = "#eab308"; glow = "0 0 3px #eab30840"; }
        else { color = "#22c55e"; glow = "0 0 3px #22c55e40"; }

        return (
          <div key={i} className="w-full rounded-[1px]"
            style={{
              height: `${100 / segments - 1}%`,
              minHeight: 3,
              backgroundColor: active ? color : "#1a1a20",
              boxShadow: active ? glow : "none",
              opacity: active ? 1 : 0.3,
            }} />
        );
      })}
    </div>
  );
}

// Stereo LED meter pair
export function StereoMeter({ left, right, className }: { left: number; right: number; className?: string }) {
  return (
    <div className={cn("flex gap-[2px]", className)}>
      <Meter value={left} className="flex-1" />
      <Meter value={right} className="flex-1" />
    </div>
  );
}
