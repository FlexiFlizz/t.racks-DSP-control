"use client";

import { useState, useCallback, useMemo, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { RotaryKnob } from "./rotary-knob";
import { cn, formatFreq, formatGain } from "@/lib/utils";
import type { PEQBand, ChannelState, CrossoverFilter } from "@/types/dsp";
import { PEQ_TYPES, CROSSOVER_SLOPES, DSP206_CONFIG } from "@/types/dsp";
import { RotateCcw, Layers, Power } from "lucide-react";

interface PEQPageProps {
  peqs: Record<string, PEQBand[]>;
  crossovers: Record<string, { hpf: CrossoverFilter; lpf: CrossoverFilter }>;
  channels: Record<string, ChannelState>;
  onBandChange: (ch: string, i: number, b: Partial<PEQBand>) => void;
  onCrossoverChange: (ch: string, type: "hpf" | "lpf", f: Partial<CrossoverFilter>) => void;
}

const BC = ["#ef4444", "#f97316", "#eab308", "#22c55e", "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#f43f5e"];
const CC: Record<string, string> = {
  "In A": "#06b6d4", "In B": "#22d3ee",
  "Out 1": "#ef4444", "Out 2": "#22c55e", "Out 3": "#eab308",
  "Out 4": "#a855f7", "Out 5": "#f97316", "Out 6": "#3b82f6",
};

// ── EQ math ──
const W = 900, H = 200, FMIN = 20, FMAX = 20000, DBR = 15;
const lr = Math.log10(FMAX / FMIN);
const f2x = (f: number) => (Math.log10(Math.max(FMIN, f) / FMIN) / lr) * W;
const x2f = (x: number) => FMIN * Math.pow(FMAX / FMIN, Math.max(0, Math.min(1, x / W)));
const d2y = (db: number) => H / 2 - (db / DBR) * (H / 2);
const y2d = (y: number) => -((y - H / 2) / (H / 2)) * DBR;

function resp(b: PEQBand, f: number): number {
  if (b.bypass || b.gain === 0) return 0;
  const r = f / b.freq;
  if (b.type === 0) return b.gain * Math.exp(-0.5 * Math.pow(Math.log2(r) * b.q * 2.5, 2));
  if (b.type === 1) return f <= b.freq ? b.gain : b.gain * Math.exp(-Math.pow(Math.log2(r) * 2.5, 2));
  if (b.type === 2) return f >= b.freq ? b.gain : b.gain * Math.exp(-Math.pow(Math.log2(1 / r) * 2.5, 2));
  return 0;
}

function mkCurve(bands: PEQBand[], s = 2): string {
  const p: string[] = [];
  for (let x = 0; x <= W; x += s) {
    const f = x2f(x); let t = 0;
    for (const b of bands) t += resp(b, f);
    p.push(`${x},${d2y(Math.max(-DBR, Math.min(DBR, t)))}`);
  }
  return `M${p.join(" L")}`;
}

function mkFill(b: PEQBand): string {
  if (b.bypass || b.gain === 0) return "";
  const z = d2y(0), p: string[] = [];
  for (let x = 0; x <= W; x += 3)
    p.push(`${x},${d2y(Math.max(-DBR, Math.min(DBR, resp(b, x2f(x)))))}`);
  return `M0,${z} L${p.join(" L")} L${W},${z} Z`;
}

const FG = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];
const FS = [30, 40, 60, 80, 150, 300, 400, 600, 800, 1500, 3000, 4000, 6000, 8000, 15000];

export function PEQPage({ peqs, crossovers, channels, onBandChange, onCrossoverChange }: PEQPageProps) {
  const all = [...DSP206_CONFIG.inputs, ...DSP206_CONFIG.outputs];
  const [ch, setCh] = useState(all[2].name);
  const [sel, setSel] = useState(0);
  const [drag, setDrag] = useState<number | null>(null);
  const [overlay, setOverlay] = useState(false);
  const svg = useRef<SVGSVGElement>(null);

  const bands = peqs[ch] || [];
  const xo = crossovers[ch];
  const b = bands[sel];
  const isOut = DSP206_CONFIG.outputs.some(o => o.name === ch);
  const bandColor = BC[sel % BC.length];

  // Keyboard
  useEffect(() => {
    const h = (e: KeyboardEvent) => {
      if (!b || ["INPUT", "SELECT"].includes((e.target as HTMLElement).tagName)) return;
      const s = e.shiftKey;
      switch (e.key) {
        case "ArrowUp": e.preventDefault(); onBandChange(ch, sel, { gain: Math.min(12, b.gain + (s ? 0.1 : 0.5)) }); break;
        case "ArrowDown": e.preventDefault(); onBandChange(ch, sel, { gain: Math.max(-12, b.gain - (s ? 0.1 : 0.5)) }); break;
        case "ArrowRight": e.preventDefault(); onBandChange(ch, sel, { freq: Math.min(20000, Math.round(b.freq * (s ? 1.01 : 1.04))) }); break;
        case "ArrowLeft": e.preventDefault(); onBandChange(ch, sel, { freq: Math.max(20, Math.round(b.freq * (s ? 0.99 : 0.96))) }); break;
        case "+": case "=": e.preventDefault(); onBandChange(ch, sel, { q: Math.min(128, +(b.q * 1.08).toFixed(2)) }); break;
        case "-": e.preventDefault(); onBandChange(ch, sel, { q: Math.max(0.4, +(b.q / 1.08).toFixed(2)) }); break;
      }
    };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [b, ch, sel, onBandChange]);

  // Curves
  const mainC = useMemo(() => mkCurve(bands), [bands]);
  const fills = useMemo(() => bands.map(mkFill), [bands]);
  const overC = useMemo(() => {
    if (!overlay) return [];
    return Object.entries(peqs).filter(([n]) => n !== ch)
      .map(([n, bs]) => ({ n, p: mkCurve(bs, 5), c: CC[n] || "#555" }));
  }, [overlay, peqs, ch]);

  // SVG drag
  const onD = useCallback((i: number, e: React.PointerEvent) => {
    e.stopPropagation(); e.preventDefault(); setDrag(i); setSel(i);
    (e.target as SVGElement).setPointerCapture(e.pointerId);
  }, []);
  const onM = useCallback((e: React.PointerEvent) => {
    if (drag === null || !svg.current) return;
    const r = svg.current.getBoundingClientRect();
    const f = Math.max(20, Math.min(20000, x2f((e.clientX - r.left) * (W / r.width))));
    const db = Math.max(-12, Math.min(12, Math.round(y2d((e.clientY - r.top) * (H / r.height)) * 10) / 10));
    onBandChange(ch, drag, { freq: Math.round(f), gain: db });
  }, [drag, ch, onBandChange]);
  const onU = useCallback(() => setDrag(null), []);

  return (
    <div className="flex flex-col gap-3 h-full">
      {/* ── Top bar: channel + tools ── */}
      <div className="flex items-center gap-1.5 flex-wrap">
        <div className="flex gap-0.5 bg-muted rounded-lg p-0.5">
          {all.map(c => (
            <button key={c.name} onClick={() => { setCh(c.name); setSel(0); }}
              className={cn("h-6 px-2 rounded-md text-[10px] font-medium transition-all",
                ch === c.name ? "bg-card text-foreground shadow-sm" : "text-muted-foreground hover:text-foreground")}
              style={{ color: ch === c.name ? CC[c.name] : undefined }}>
              {channels[c.name]?.label || c.name}
            </button>
          ))}
        </div>
        <div className="flex-1" />
        <Button variant={overlay ? "default" : "ghost"} size="sm" className="h-6 text-[10px] gap-1"
          onClick={() => setOverlay(!overlay)}>
          <Layers className="w-3 h-3" /> Overlay
        </Button>
        <Button variant="ghost" size="sm" className="h-6 text-[10px] gap-1"
          onClick={() => bands.forEach((_, i) => onBandChange(ch, i, { gain: 0 }))}>
          <RotateCcw className="w-3 h-3" /> Reset
        </Button>
      </div>

      {/* ── Main area: curve + knobs panel ── */}
      <div className="flex gap-3 flex-1 min-h-0">
        {/* EQ Curve */}
        <div className="flex-1 min-w-0 rounded-xl border border-border bg-gradient-to-b from-card to-[#08080c] overflow-hidden">
          <svg ref={svg} viewBox={`0 0 ${W} ${H}`} className="w-full h-full" preserveAspectRatio="xMidYMid meet"
            onPointerMove={onM} onPointerUp={onU}>
            {/* Sub grid */}
            {FS.map(f => <line key={f} x1={f2x(f)} y1={0} x2={f2x(f)} y2={H} stroke="var(--color-border)" strokeOpacity={0.2} />)}
            {/* Main freq grid */}
            {FG.map(f => (
              <g key={f}>
                <line x1={f2x(f)} y1={0} x2={f2x(f)} y2={H} stroke="var(--color-border)" strokeOpacity={0.5} />
                <text x={f2x(f)} y={H - 5} textAnchor="middle" fill="var(--color-muted-foreground)" fillOpacity={0.4} fontSize="8" fontFamily="var(--font-mono)">{formatFreq(f)}</text>
              </g>
            ))}
            {/* dB lines */}
            {[-12, -6, 0, 6, 12].map(db => (
              <g key={db}>
                <line x1={0} y1={d2y(db)} x2={W} y2={d2y(db)} stroke="var(--color-border)" strokeOpacity={db === 0 ? 0.7 : 0.25} strokeWidth={db === 0 ? 0.8 : 0.5} />
                <text x={8} y={d2y(db) - 3} fill="var(--color-muted-foreground)" fillOpacity={0.25} fontSize="8" fontFamily="var(--font-mono)">{db > 0 ? `+${db}` : db}</text>
              </g>
            ))}

            {/* Overlays */}
            {overC.map(({ n, p, c }) => <path key={n} d={p} fill="none" stroke={c} strokeWidth={1} strokeOpacity={0.2} strokeDasharray="4 2" />)}
            {/* HPF/LPF zones */}
            {xo?.hpf.active && <rect x={0} y={0} width={f2x(xo.hpf.freq)} height={H} fill="#000" fillOpacity={0.3} rx={0} />}
            {xo?.lpf.active && <rect x={f2x(xo.lpf.freq)} y={0} width={W - f2x(xo.lpf.freq)} height={H} fill="#000" fillOpacity={0.3} />}
            {/* Band fills */}
            {fills.map((f, i) => f && <path key={`fl${i}`} d={f} fill={BC[i]} fillOpacity={sel === i ? 0.15 : 0.04} />)}
            {/* Main curve */}
            <path d={mainC} fill="none" stroke="var(--color-foreground)" strokeOpacity={0.6} strokeWidth={1.5} />

            {/* Band dots - EQ Eight style */}
            {bands.map((band, i) => {
              const cx = f2x(band.freq), cy = d2y(band.gain), c = BC[i], s = sel === i;
              return (
                <g key={i} onPointerDown={e => onD(i, e)} className="cursor-grab active:cursor-grabbing">
                  <circle cx={cx} cy={cy} r={20} fill="transparent" />
                  {s && <circle cx={cx} cy={cy} r={14} fill={c} fillOpacity={0.08} />}
                  <circle cx={cx} cy={cy} r={s ? 7 : 5} fill={s ? c : "none"} stroke={c}
                    strokeWidth={s ? 0 : 1.5} opacity={band.bypass ? 0.15 : 1} />
                  <text x={cx} y={cy + (s ? 3.5 : 3)} textAnchor="middle"
                    fill={s ? "#000" : c} fontSize={s ? "8" : "7"} fontWeight="bold"
                    fontFamily="var(--font-sans)" opacity={band.bypass ? 0.15 : 1}>{i + 1}</text>
                  {s && !band.bypass && (
                    <text x={cx} y={Math.max(12, cy - 18)} textAnchor="middle"
                      fill="var(--color-muted-foreground)" fontSize="8" fontFamily="var(--font-mono)">
                      {formatFreq(band.freq)} Hz  |  {formatGain(band.gain)} dB  |  Q {band.q.toFixed(1)}
                    </text>
                  )}
                </g>
              );
            })}
          </svg>
        </div>

        {/* ── Knobs panel (right side) ── */}
        {b && (
          <div className="w-[180px] flex-shrink-0 rounded-xl border border-border bg-gradient-to-b from-card to-[#08080c] p-3 flex flex-col gap-4">
            {/* Band selector */}
            <div className="flex flex-wrap gap-1 justify-center">
              {bands.map((band, i) => (
                <button key={i} onClick={() => setSel(i)}
                  className={cn("w-6 h-6 rounded-md text-[9px] font-bold transition-all",
                    sel === i ? "text-black shadow-md" : "bg-muted text-muted-foreground/50 hover:text-foreground",
                    band.bypass && sel !== i && "opacity-15")}
                  style={{
                    backgroundColor: sel === i ? BC[i] : undefined,
                    boxShadow: sel === i ? `0 0 8px ${BC[i]}40` : undefined,
                  }}>
                  {i + 1}
                </button>
              ))}
            </div>

            {/* Band on/off + type */}
            <div className="flex items-center gap-2 justify-center">
              <button onClick={() => onBandChange(ch, sel, { bypass: !b.bypass })}
                className={cn("w-7 h-7 rounded-lg flex items-center justify-center transition-all border",
                  b.bypass ? "bg-muted border-border text-muted-foreground/40" : "border-transparent")}
                style={{ backgroundColor: b.bypass ? undefined : bandColor + "20", color: b.bypass ? undefined : bandColor }}>
                <Power className="w-3.5 h-3.5" />
              </button>
              <select value={b.type} onChange={e => onBandChange(ch, sel, { type: +e.target.value })}
                className="flex-1 h-7 rounded-lg bg-muted border border-border text-[10px] px-1.5 outline-none text-foreground">
                {PEQ_TYPES.map((n, i) => <option key={i} value={i}>{n}</option>)}
              </select>
            </div>

            {/* Knobs */}
            <div className="flex flex-col items-center gap-3">
              <RotaryKnob
                label="Frequency"
                value={b.freq}
                min={20} max={20000}
                onChange={v => onBandChange(ch, sel, { freq: Math.round(v) })}
                display={`${formatFreq(b.freq)} Hz`}
                color={bandColor}
                logarithmic
                size={56}
              />
              <RotaryKnob
                label="Gain"
                value={b.gain}
                min={-12} max={12}
                onChange={v => onBandChange(ch, sel, { gain: Math.round(v * 10) / 10 })}
                display={`${formatGain(b.gain)} dB`}
                color={b.gain > 0 ? "#ef4444" : b.gain < 0 ? "#22c55e" : bandColor}
                size={56}
              />
              <RotaryKnob
                label="Q"
                value={b.q}
                min={0.4} max={30}
                onChange={v => onBandChange(ch, sel, { q: +v.toFixed(2) })}
                display={b.q.toFixed(2)}
                color={bandColor}
                logarithmic
                size={56}
              />
            </div>

            {/* HPF / LPF (outputs only) */}
            {isOut && xo && (
              <>
                <div className="h-px bg-border" />
                <div className="flex gap-2 justify-center">
                  {/* HPF */}
                  <div className="flex flex-col items-center gap-1">
                    <button onClick={() => onCrossoverChange(ch, "hpf", { active: !xo.hpf.active })}
                      className={cn("h-5 px-2 rounded-md text-[8px] font-bold transition-all",
                        xo.hpf.active ? "bg-blue-500/20 text-blue-400 shadow-[0_0_6px_rgba(59,130,246,0.2)]" : "bg-muted text-muted-foreground/30")}>
                      HPF
                    </button>
                    {xo.hpf.active && (
                      <RotaryKnob label="" value={xo.hpf.freq} min={20} max={5000} logarithmic size={40}
                        onChange={v => onCrossoverChange(ch, "hpf", { freq: Math.round(v) })}
                        display={`${formatFreq(xo.hpf.freq)}`} color="#3b82f6" />
                    )}
                  </div>
                  {/* LPF */}
                  <div className="flex flex-col items-center gap-1">
                    <button onClick={() => onCrossoverChange(ch, "lpf", { active: !xo.lpf.active })}
                      className={cn("h-5 px-2 rounded-md text-[8px] font-bold transition-all",
                        xo.lpf.active ? "bg-red-500/20 text-red-400 shadow-[0_0_6px_rgba(239,68,68,0.2)]" : "bg-muted text-muted-foreground/30")}>
                      LPF
                    </button>
                    {xo.lpf.active && (
                      <RotaryKnob label="" value={xo.lpf.freq} min={200} max={20000} logarithmic size={40}
                        onChange={v => onCrossoverChange(ch, "lpf", { freq: Math.round(v) })}
                        display={`${formatFreq(xo.lpf.freq)}`} color="#ef4444" />
                    )}
                  </div>
                </div>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
