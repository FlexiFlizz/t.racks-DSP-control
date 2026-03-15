"use client";

import { useState } from "react";
import { TooltipProvider } from "@/components/ui/tooltip";
import { GainPage } from "@/components/dsp/page-gain";
import { PEQPage } from "@/components/dsp/page-peq";
import { GEQSection } from "@/components/dsp/geq-section";
import { MatrixSection } from "@/components/dsp/matrix-section";
import { DelaySection } from "@/components/dsp/delay-section";
import { PresetsSection } from "@/components/dsp/presets-section";
import { useDSPStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { SlidersHorizontal, Activity, BarChart3, Grid3X3, Timer, Save, Wifi, WifiOff } from "lucide-react";

const TABS = [
  { id: "gain", label: "Gain", icon: SlidersHorizontal },
  { id: "peq", label: "PEQ", icon: Activity },
  { id: "geq", label: "GEQ", icon: BarChart3 },
  { id: "matrix", label: "Matrix", icon: Grid3X3 },
  { id: "delay", label: "Delay", icon: Timer },
  { id: "presets", label: "Presets", icon: Save },
];

export default function Home() {
  const store = useDSPStore();
  const [tab, setTab] = useState("peq");

  return (
    <TooltipProvider>
      <div className="flex flex-col h-screen overflow-hidden">
        {/* Header */}
        <header className="flex items-center h-10 px-3 bg-card border-b border-border flex-shrink-0 gap-1">
          <div className="flex items-center gap-2 mr-4">
            <div className="h-6 w-6 rounded-md bg-primary/15 border border-primary/25 flex items-center justify-center">
              <span className="text-[9px] font-black text-primary">t.</span>
            </div>
            <span className="text-xs font-bold text-foreground/80">DSP 206</span>
          </div>

          <nav className="flex items-center gap-0.5">
            {TABS.map(t => {
              const Icon = t.icon;
              return (
                <button key={t.id} onClick={() => setTab(t.id)}
                  className={cn(
                    "flex items-center gap-1.5 h-7 px-2.5 rounded-md text-[11px] font-medium transition-all",
                    tab === t.id
                      ? "bg-primary/15 text-primary"
                      : "text-muted-foreground hover:text-foreground hover:bg-muted",
                  )}>
                  <Icon className="w-3.5 h-3.5" />
                  {t.label}
                </button>
              );
            })}
          </nav>

          <button onClick={() => store.setConnected(!store.connected)}
            className={cn(
              "ml-auto flex items-center gap-1.5 px-2.5 h-7 rounded-full text-[10px] font-semibold border",
              store.connected
                ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                : "bg-muted text-muted-foreground border-border",
            )}>
            {store.connected ? <Wifi className="w-3 h-3" /> : <WifiOff className="w-3 h-3" />}
            {store.connected ? "Online" : "Offline"}
          </button>
        </header>

        {/* Content */}
        <main className="flex-1 overflow-auto p-3">
          {tab === "gain" && (
            <GainPage channels={store.channels}
              onGainChange={store.setGain}
              onMuteToggle={ch => store.setMute(ch, !store.channels[ch].mute)}
              onPhaseToggle={ch => store.setPhase(ch, !store.channels[ch].phase)}
              onLabelChange={store.setLabel} />
          )}
          {tab === "peq" && (
            <PEQPage peqs={store.peqs} crossovers={store.crossovers} channels={store.channels}
              onBandChange={store.setPEQBand} onCrossoverChange={store.setCrossover} />
          )}
          {tab === "geq" && <GEQSection geqs={store.geqs} onBandChange={store.setGEQBand} />}
          {tab === "matrix" && <MatrixSection matrix={store.matrix} onRoutingChange={store.setMatrixRouting} />}
          {tab === "delay" && <DelaySection delays={store.delays} onDelayChange={store.setDelay} />}
          {tab === "presets" && <PresetsSection presets={store.presets} onLoadPreset={store.setActivePreset} />}
        </main>

        <footer className="flex-shrink-0 h-5 px-3 flex items-center border-t border-border text-[9px] text-muted-foreground font-mono gap-4">
          <span>TCP :9761</span><span>2in/6out</span><span className="ml-auto">v0.1</span>
        </footer>
      </div>
    </TooltipProvider>
  );
}
