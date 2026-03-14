"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { StatusBadge } from "@/components/status-badge";
import { Terminal } from "@/components/terminal";
import { FreqChart } from "@/components/charts/freq-chart";
import {
  rewStatus, rewMesures, rewFreqResponse,
  dspStatus, dspConnect, dspSetDelay,
  calageDelay, calageEQ,
  getSysteme, saveSysteme,
  type Systeme, type Enceinte, type Paire,
} from "@/lib/api";
import { PresetPicker } from "@/components/preset-picker";
import { type PresetEnceinte } from "@/lib/api";
import {
  Plus, Trash2, Play, RefreshCw, Plug, Target, SlidersHorizontal,
  Volume2, Waves, TerminalSquare, ScrollText, LineChart,
  Check, AlertTriangle, Loader2, ArrowRight, Timer, Settings2,
  GitCompare, Search, Speaker,
} from "lucide-react";

const TYPES_ENCEINTE = [
  { value: "sub", label: "Sub" },
  { value: "top", label: "Top / Main" },
  { value: "low_mid", label: "Low-Mid" },
  { value: "high", label: "High" },
  { value: "fill", label: "Fill" },
  { value: "delay", label: "Delay" },
  { value: "monitor", label: "Monitor" },
];

const CANAUX = ["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"];

export default function CalagePage() {
  const [mode, setMode] = useState<"script" | "ia">("script");
  const [etape, setEtape] = useState<"systeme" | "calage">("systeme");
  const [rewOk, setRewOk] = useState(false);
  const [dspOk, setDspOk] = useState(false);
  const [mesures, setMesures] = useState<any[]>([]);
  const [running, setRunning] = useState(false);
  const [loading, setLoading] = useState(false);
  const [journal, setJournal] = useState<string[]>([]);

  // Systeme
  const [systeme, setSysteme] = useState<Systeme>({
    nom: "Mon systeme", ip_dsp: "127.0.0.1", port_dsp: 9761, enceintes: [], paires: [],
  });

  // Paire selectionnee
  const [paireActive, setPaireActive] = useState<string | null>(null);
  const [calageTab, setCalageTab] = useState<"delay" | "phase" | "eq">("delay");

  // Resultats
  const [resultatDelay, setResultatDelay] = useState<any>(null);
  const [resultatEQ, setResultatEQ] = useState<any>(null);

  // Charts
  const [chartA, setChartA] = useState<any>(null);
  const [chartB, setChartB] = useState<any>(null);
  const [chartMode, setChartMode] = useState<"magnitude" | "phase">("magnitude");
  const [presetPickerOpen, setPresetPickerOpen] = useState(false);

  const log = (msg: string) => setJournal((j) => [...j, `[${new Date().toLocaleTimeString()}] ${msg}`]);
  const exec = (cmd: string) => { log(`> ${cmd}`); (window as any).__terminalExecute?.(cmd); };

  const refreshStatus = useCallback(async () => {
    try { const r = await rewStatus(); setRewOk(r.connecte); if (r.connecte) { const m = await rewMesures(); setMesures(m); } } catch { setRewOk(false); }
    try { const d = await dspStatus(); setDspOk(d.connecte); } catch { setDspOk(false); }
  }, []);

  useEffect(() => {
    refreshStatus();
    getSysteme().then(setSysteme).catch(() => {});
    const id = setInterval(refreshStatus, 5000);
    return () => clearInterval(id);
  }, [refreshStatus]);

  const sauvegarder = async (s: Systeme) => {
    setSysteme(s);
    await saveSysteme(s).catch(() => {});
  };

  // -- Enceintes --
  const ajouterEnceinte = () => {
    const id = `enc_${Date.now()}`;
    const s = { ...systeme, enceintes: [...systeme.enceintes, { id, nom: "", type: "top", canal_dsp: "Out 1" }] };
    sauvegarder(s);
  };
  const majEnceinte = (id: string, updates: Partial<Enceinte>) => {
    const s = { ...systeme, enceintes: systeme.enceintes.map((e) => e.id === id ? { ...e, ...updates } : e) };
    sauvegarder(s);
  };
  const suppEnceinte = (id: string) => {
    const s = { ...systeme, enceintes: systeme.enceintes.filter((e) => e.id !== id), paires: systeme.paires.filter((p) => p.enceinte_bas !== id && p.enceinte_haut !== id) };
    sauvegarder(s);
  };

  // -- Paires --
  const ajouterPaire = () => {
    if (systeme.enceintes.length < 2) return;
    const id = `paire_${Date.now()}`;
    const bas = systeme.enceintes[0];
    const haut = systeme.enceintes[1] || systeme.enceintes[0];
    // Auto-crossover : LPF du bas ou HPF du haut
    const crossover = bas.lpf_hz || haut.hpf_hz || 120;
    const s = { ...systeme, paires: [...systeme.paires, { id, enceinte_bas: bas.id, enceinte_haut: haut.id, crossover_hz: crossover }] };
    sauvegarder(s);
  };
  const majPaire = (id: string, updates: Partial<Paire>) => {
    const s = { ...systeme, paires: systeme.paires.map((p) => {
      if (p.id !== id) return p;
      const updated = { ...p, ...updates };
      // Auto-crossover quand on change les enceintes
      if (updates.enceinte_bas || updates.enceinte_haut) {
        const bas = systeme.enceintes.find((e) => e.id === (updates.enceinte_bas || p.enceinte_bas));
        const haut = systeme.enceintes.find((e) => e.id === (updates.enceinte_haut || p.enceinte_haut));
        const autoCross = bas?.lpf_hz || haut?.hpf_hz;
        if (autoCross) updated.crossover_hz = autoCross;
      }
      return updated;
    })};
    sauvegarder(s);
  };
  const suppPaire = (id: string) => {
    const s = { ...systeme, paires: systeme.paires.filter((p) => p.id !== id) };
    sauvegarder(s);
    if (paireActive === id) setPaireActive(null);
  };

  const getEnc = (id: string) => systeme.enceintes.find((e) => e.id === id);
  const paire = systeme.paires.find((p) => p.id === paireActive);

  // -- Charger courbes de la paire --
  const chargerCourbes = async () => {
    if (!paire) return;
    log("Chargement des courbes...");
    if (paire.mesure_bas != null) { try { setChartA(await rewFreqResponse(paire.mesure_bas)); } catch { log("Erreur chargement mesure basse"); } }
    if (paire.mesure_haut != null) { try { setChartB(await rewFreqResponse(paire.mesure_haut)); } catch { log("Erreur chargement mesure haute"); } }
  };

  // -- Analyser delay --
  const analyserDelay = async () => {
    if (!paire || paire.mesure_bas == null || paire.mesure_haut == null) { log("Assigner les mesures REW d'abord"); return; }
    const enc = getEnc(paire.enceinte_haut);
    setLoading(true); setResultatDelay(null);
    log(`Analyse delay : ${getEnc(paire.enceinte_bas)?.nom} / ${enc?.nom} @ ${paire.crossover_hz} Hz`);
    try {
      const r = await calageDelay({ index_mesure_a: paire.mesure_bas, index_mesure_b: paire.mesure_haut, freq_crossover: paire.crossover_hz, canal_delay: enc?.canal_dsp || "Out 1", appliquer: false });
      setResultatDelay(r);
      r.messages?.forEach((m: string) => log(m));
      majPaire(paire.id, { delay_ms: r.delay_ms, inverser_polarite: r.inverser_polarite, coherence: r.coherence_phase });
    } catch (e: any) { log(`ERREUR : ${e.message}`); }
    setLoading(false);
  };

  // -- Analyser EQ --
  const analyserEQ = async () => {
    if (!paire || paire.mesure_bas == null) { log("Assigner les mesures REW d'abord"); return; }
    const enc = getEnc(paire.enceinte_bas);
    setLoading(true); setResultatEQ(null);
    log(`Analyse EQ : ${enc?.nom}`);
    try {
      const r = await calageEQ({ index_mesure: paire.mesure_bas, canal_dsp: enc?.canal_dsp || "Out 1", appliquer: false });
      setResultatEQ(r);
      r.messages?.forEach((m: string) => log(m));
      majPaire(paire.id, { filtres_eq: r.filtres });
    } catch (e: any) { log(`ERREUR : ${e.message}`); }
    setLoading(false);
  };

  const appliquerDelay = async () => {
    if (!resultatDelay || !paire) return;
    const enc = getEnc(paire.enceinte_haut);
    log(`Appliquer delay ${resultatDelay.delay_ms} ms sur ${enc?.canal_dsp}`);
    try { await dspSetDelay(enc?.canal_dsp || "Out 1", resultatDelay.delay_ms); log("Delay applique."); } catch (e: any) { log(`ERREUR : ${e.message}`); }
  };

  const appliquerEQ = async () => {
    if (!resultatEQ?.filtres?.length || !paire) return;
    const enc = getEnc(paire.enceinte_bas);
    log(`Appliquer EQ sur ${enc?.canal_dsp}`);
    try { await calageEQ({ index_mesure: paire.mesure_bas!, canal_dsp: enc?.canal_dsp || "Out 1", appliquer: true }); log("EQ applique."); } catch (e: any) { log(`ERREUR : ${e.message}`); }
  };

  const connectDsp = async () => {
    try { await dspConnect(systeme.ip_dsp, systeme.port_dsp); setDspOk(true); log("DSP connecte"); } catch { log("Echec connexion DSP"); }
  };

  return (
    <div className="space-y-4">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Calage</h2>
          <p className="text-muted-foreground text-sm">{systeme.nom}</p>
        </div>
        <div className="flex gap-2">
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            <button onClick={() => setEtape("systeme")} className={`px-3 py-1.5 text-xs rounded-md transition-colors ${etape === "systeme" ? "bg-background text-foreground font-medium shadow-sm" : "text-muted-foreground"}`}>
              <Settings2 className="h-3.5 w-3.5 inline mr-1" />Systeme
            </button>
            <button onClick={() => setEtape("calage")} className={`px-3 py-1.5 text-xs rounded-md transition-colors ${etape === "calage" ? "bg-background text-foreground font-medium shadow-sm" : "text-muted-foreground"}`}>
              <Target className="h-3.5 w-3.5 inline mr-1" />Calage
            </button>
          </div>
          <div className="flex gap-1 bg-muted rounded-lg p-1">
            <button onClick={() => setMode("script")} className={`px-2 py-1.5 text-xs rounded-md ${mode === "script" ? "bg-background shadow-sm" : "text-muted-foreground"}`}>Script</button>
            <button onClick={() => setMode("ia")} className={`px-2 py-1.5 text-xs rounded-md ${mode === "ia" ? "bg-background shadow-sm" : "text-muted-foreground"}`}>IA</button>
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="flex items-center gap-3 flex-wrap">
        <StatusBadge connected={rewOk} label={rewOk ? "REW" : "REW off"} />
        <StatusBadge connected={dspOk} label={dspOk ? "DSP" : "DSP off"} />
        {rewOk && <Badge variant="outline" className="text-xs">{mesures.length} mesure{mesures.length !== 1 ? "s" : ""}</Badge>}
        <Button size="sm" variant="ghost" onClick={refreshStatus}><RefreshCw className="h-3.5 w-3.5" /></Button>
        {!dspOk && <Button size="sm" variant="outline" onClick={connectDsp} className="ml-auto"><Plug className="h-3.5 w-3.5 mr-1" />Connecter DSP</Button>}
      </div>

      {/* ========== ONGLET SYSTEME ========== */}
      {etape === "systeme" && (
        <>
          {/* Config DSP */}
          <Card>
            <CardContent className="pt-4">
              <div className="grid grid-cols-3 gap-3">
                <div>
                  <label className="text-[11px] text-muted-foreground">Nom du systeme</label>
                  <input type="text" value={systeme.nom} onChange={(e) => sauvegarder({ ...systeme, nom: e.target.value })} className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground">IP du DSP</label>
                  <input type="text" value={systeme.ip_dsp} onChange={(e) => sauvegarder({ ...systeme, ip_dsp: e.target.value })} className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                </div>
                <div>
                  <label className="text-[11px] text-muted-foreground">Port</label>
                  <input type="number" value={systeme.port_dsp} onChange={(e) => sauvegarder({ ...systeme, port_dsp: Number(e.target.value) })} className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Enceintes */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Enceintes ({systeme.enceintes.length})</CardTitle>
                <div className="flex gap-2">
                  <Button size="sm" variant="outline" onClick={() => setPresetPickerOpen(true)}><Speaker className="h-3.5 w-3.5 mr-1" />Depuis preset</Button>
                  <Button size="sm" variant="ghost" onClick={ajouterEnceinte}><Plus className="h-3.5 w-3.5 mr-1" />Vide</Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {systeme.enceintes.length === 0 && <p className="text-sm text-muted-foreground py-4 text-center">Ajoute tes enceintes pour commencer.</p>}
              {systeme.enceintes.map((e) => (
                <div key={e.id} className="flex items-center gap-2 bg-muted/50 p-2 rounded-lg">
                  <input type="text" value={e.nom} placeholder="Nom (ex: Sub L)" onChange={(ev) => majEnceinte(e.id, { nom: ev.target.value })} className="bg-muted border border-border rounded px-2 py-1 text-sm flex-1" />
                  <select value={e.type} onChange={(ev) => majEnceinte(e.id, { type: ev.target.value })} className="bg-muted border border-border rounded px-2 py-1 text-sm w-28">
                    {TYPES_ENCEINTE.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                  </select>
                  <select value={e.canal_dsp} onChange={(ev) => majEnceinte(e.id, { canal_dsp: ev.target.value })} className="bg-muted border border-border rounded px-2 py-1 text-sm w-20">
                    {CANAUX.map((c) => <option key={c}>{c}</option>)}
                  </select>
                  <input type="number" value={e.hpf_hz || ""} placeholder="HPF" onChange={(ev) => majEnceinte(e.id, { hpf_hz: ev.target.value ? Number(ev.target.value) : null })} className="bg-muted border border-border rounded px-2 py-1 text-xs font-mono w-16" title="HPF (Hz)" />
                  <input type="number" value={e.lpf_hz || ""} placeholder="LPF" onChange={(ev) => majEnceinte(e.id, { lpf_hz: ev.target.value ? Number(ev.target.value) : null })} className="bg-muted border border-border rounded px-2 py-1 text-xs font-mono w-16" title="LPF (Hz)" />
                  <Button size="sm" variant="ghost" onClick={() => suppEnceinte(e.id)}><Trash2 className="h-3.5 w-3.5 text-red-400" /></Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {/* Paires */}
          <Card>
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <CardTitle className="text-sm font-medium">Paires a caler ({systeme.paires.length})</CardTitle>
                <Button size="sm" variant="outline" onClick={ajouterPaire} disabled={systeme.enceintes.length < 2}><Plus className="h-3.5 w-3.5 mr-1" />Ajouter</Button>
              </div>
            </CardHeader>
            <CardContent className="space-y-2">
              {systeme.paires.length === 0 && <p className="text-sm text-muted-foreground py-4 text-center">Ajoute des paires d&apos;enceintes a caler ensemble.</p>}
              {systeme.paires.map((p) => (
                <div key={p.id} className="flex items-center gap-2 bg-muted/50 p-2 rounded-lg">
                  <select value={p.enceinte_bas} onChange={(ev) => majPaire(p.id, { enceinte_bas: ev.target.value })} className="bg-muted border border-border rounded px-2 py-1 text-sm flex-1">
                    {systeme.enceintes.map((e) => <option key={e.id} value={e.id}>{e.nom || e.id}</option>)}
                  </select>
                  <span className="text-xs text-muted-foreground">↔</span>
                  <select value={p.enceinte_haut} onChange={(ev) => majPaire(p.id, { enceinte_haut: ev.target.value })} className="bg-muted border border-border rounded px-2 py-1 text-sm flex-1">
                    {systeme.enceintes.map((e) => <option key={e.id} value={e.id}>{e.nom || e.id}</option>)}
                  </select>
                  <input type="number" value={p.crossover_hz} onChange={(ev) => majPaire(p.id, { crossover_hz: Number(ev.target.value) })} className="bg-muted border border-border rounded px-2 py-1 text-xs font-mono w-20" title="Crossover Hz" />
                  <span className="text-[10px] text-muted-foreground">Hz</span>
                  {p.coherence != null && (
                    <Badge variant="outline" className={`text-[10px] ${p.coherence > 0.8 ? "text-green-400 border-green-500/50" : p.coherence > 0.6 ? "text-yellow-400 border-yellow-500/50" : "text-red-400 border-red-500/50"}`}>
                      {(p.coherence * 100).toFixed(0)}%
                    </Badge>
                  )}
                  <Button size="sm" variant="ghost" onClick={() => suppPaire(p.id)}><Trash2 className="h-3.5 w-3.5 text-red-400" /></Button>
                </div>
              ))}
            </CardContent>
          </Card>

          {systeme.enceintes.length >= 2 && systeme.paires.length > 0 && (
            <Button onClick={() => setEtape("calage")}><ArrowRight className="h-4 w-4 mr-1" />Passer au calage</Button>
          )}
        </>
      )}

      {/* ========== ONGLET CALAGE ========== */}
      {etape === "calage" && (
        <>
          {/* Selection paire */}
          <div className="flex gap-2 flex-wrap">
            {systeme.paires.map((p) => {
              const eb = getEnc(p.enceinte_bas);
              const eh = getEnc(p.enceinte_haut);
              return (
                <Button key={p.id} size="sm" variant={paireActive === p.id ? "default" : "outline"} onClick={() => { setPaireActive(p.id); setResultatDelay(null); setResultatEQ(null); setChartA(null); setChartB(null); }}>
                  {eb?.nom || "?"} ↔ {eh?.nom || "?"} ({p.crossover_hz} Hz)
                </Button>
              );
            })}
          </div>

          {paire && (
            <>
              {/* Assigner mesures REW */}
              <Card>
                <CardContent className="pt-4">
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div>
                      <label className="text-[11px] text-muted-foreground">Mesure {getEnc(paire.enceinte_bas)?.nom}</label>
                      <select value={paire.mesure_bas ?? ""} onChange={(e) => majPaire(paire.id, { mesure_bas: e.target.value ? Number(e.target.value) : null })} className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm">
                        <option value="">-- Choisir --</option>
                        {mesures.map((m, i) => <option key={i} value={i}>[{i}] {m.name || `Mesure ${i}`}</option>)}
                      </select>
                    </div>
                    <div>
                      <label className="text-[11px] text-muted-foreground">Mesure {getEnc(paire.enceinte_haut)?.nom}</label>
                      <select value={paire.mesure_haut ?? ""} onChange={(e) => majPaire(paire.id, { mesure_haut: e.target.value ? Number(e.target.value) : null })} className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm">
                        <option value="">-- Choisir --</option>
                        {mesures.map((m, i) => <option key={i} value={i}>[{i}] {m.name || `Mesure ${i}`}</option>)}
                      </select>
                    </div>
                    <div className="flex items-end">
                      <Button size="sm" variant="outline" className="w-full" onClick={chargerCourbes} disabled={paire.mesure_bas == null && paire.mesure_haut == null}>
                        <LineChart className="h-3.5 w-3.5 mr-1" />Courbes
                      </Button>
                    </div>
                    <div className="flex items-end">
                      <Button size="sm" variant="ghost" className="w-full" onClick={refreshStatus}><RefreshCw className="h-3.5 w-3.5 mr-1" />Rafraichir</Button>
                    </div>
                  </div>
                </CardContent>
              </Card>

              {/* Courbes */}
              {(chartA || chartB) && (
                <Card>
                  <CardHeader className="pb-2">
                    <div className="flex items-center justify-between">
                      <CardTitle className="text-sm font-medium">Courbes</CardTitle>
                      <div className="flex gap-1">
                        <Button size="sm" variant={chartMode === "magnitude" ? "default" : "ghost"} className="h-6 text-xs px-2" onClick={() => setChartMode("magnitude")}>SPL</Button>
                        <Button size="sm" variant={chartMode === "phase" ? "default" : "ghost"} className="h-6 text-xs px-2" onClick={() => setChartMode("phase")}>Phase</Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <FreqChart dataA={chartA} dataB={chartB} mode={chartMode}
                      labelA={getEnc(paire.enceinte_bas)?.nom || "Bas"}
                      labelB={getEnc(paire.enceinte_haut)?.nom || "Haut"}
                      crossoverHz={paire.crossover_hz} />
                  </CardContent>
                </Card>
              )}

              {/* Onglets Delay / Phase / EQ */}
              {mode === "script" && (
                <Tabs value={calageTab} onValueChange={(v) => setCalageTab(v as any)}>
                  <TabsList>
                    <TabsTrigger value="delay" className="gap-1"><Timer className="h-3.5 w-3.5" />Delay</TabsTrigger>
                    <TabsTrigger value="phase" className="gap-1"><Waves className="h-3.5 w-3.5" />Phase</TabsTrigger>
                    <TabsTrigger value="eq" className="gap-1"><SlidersHorizontal className="h-3.5 w-3.5" />EQ</TabsTrigger>
                  </TabsList>

                  <TabsContent value="delay" className="space-y-3 mt-3">
                    <Button onClick={analyserDelay} disabled={loading || paire.mesure_bas == null || paire.mesure_haut == null}>
                      {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <Target className="h-4 w-4 mr-1" />}
                      Calculer delay
                    </Button>
                    {resultatDelay && (
                      <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                        <div className="bg-muted p-3 rounded-lg"><div className="text-[11px] text-muted-foreground">Delay</div><div className="text-lg font-bold font-mono">{resultatDelay.delay_ms?.toFixed(2)} ms</div></div>
                        <div className="bg-muted p-3 rounded-lg"><div className="text-[11px] text-muted-foreground">Appliquer sur</div><div className="text-lg font-bold">{resultatDelay.appliquer_sur}</div></div>
                        <div className="bg-muted p-3 rounded-lg"><div className="text-[11px] text-muted-foreground">Polarite</div>{resultatDelay.inverser_polarite ? <div className="flex items-center gap-1 text-yellow-400 font-bold"><AlertTriangle className="h-4 w-4" />INVERSER</div> : <div className="flex items-center gap-1 text-green-400 font-bold"><Check className="h-4 w-4" />OK</div>}</div>
                        <div className="bg-muted p-3 rounded-lg"><div className="text-[11px] text-muted-foreground">Coherence</div><div className={`text-lg font-bold font-mono ${resultatDelay.coherence_phase > 0.8 ? "text-green-400" : resultatDelay.coherence_phase > 0.6 ? "text-yellow-400" : "text-red-400"}`}>{(resultatDelay.coherence_phase * 100).toFixed(0)}%</div></div>
                      </div>
                    )}
                    {resultatDelay && <Button size="sm" onClick={appliquerDelay} disabled={!dspOk}><ArrowRight className="h-3.5 w-3.5 mr-1" />Appliquer delay</Button>}
                  </TabsContent>

                  <TabsContent value="phase" className="space-y-3 mt-3">
                    <p className="text-sm text-muted-foreground">La detection de polarite est incluse dans l&apos;analyse delay. Pour les filtres all-pass, utilise le terminal.</p>
                    {resultatDelay?.inverser_polarite && (
                      <div className="flex items-center gap-2 bg-yellow-500/10 border border-yellow-500/30 p-3 rounded-lg">
                        <AlertTriangle className="h-5 w-5 text-yellow-400" />
                        <div><div className="font-medium text-sm">Polarite a inverser</div><div className="text-xs text-muted-foreground">Inverse la polarite sur le DSP ou dans la connexion physique.</div></div>
                      </div>
                    )}
                    {resultatDelay && !resultatDelay.inverser_polarite && (
                      <div className="flex items-center gap-2 bg-green-500/10 border border-green-500/30 p-3 rounded-lg">
                        <Check className="h-5 w-5 text-green-400" />
                        <div className="font-medium text-sm">Polarite OK</div>
                      </div>
                    )}
                  </TabsContent>

                  <TabsContent value="eq" className="space-y-3 mt-3">
                    <Button onClick={analyserEQ} disabled={loading || paire.mesure_bas == null}>
                      {loading ? <Loader2 className="h-4 w-4 mr-1 animate-spin" /> : <SlidersHorizontal className="h-4 w-4 mr-1" />}
                      Calculer EQ correctif
                    </Button>
                    {resultatEQ?.filtres?.length > 0 && (
                      <>
                        <table className="w-full text-xs font-mono">
                          <thead><tr className="text-muted-foreground border-b border-border"><th className="text-left py-1 pr-4">Bande</th><th className="text-right py-1 pr-4">Freq</th><th className="text-right py-1 pr-4">Gain</th><th className="text-right py-1">Q</th></tr></thead>
                          <tbody>{resultatEQ.filtres.map((f: any, i: number) => (
                            <tr key={i} className="border-b border-border/50"><td className="py-1.5 pr-4">{i}</td><td className="text-right py-1.5 pr-4">{f.frequence_hz?.toFixed(0)} Hz</td><td className="text-right py-1.5 pr-4 text-red-400">{f.gain_db?.toFixed(1)} dB</td><td className="text-right py-1.5">{f.q?.toFixed(1)}</td></tr>
                          ))}</tbody>
                        </table>
                        <Button size="sm" onClick={appliquerEQ} disabled={!dspOk}><ArrowRight className="h-3.5 w-3.5 mr-1" />Appliquer EQ</Button>
                      </>
                    )}
                    {resultatEQ?.filtres?.length === 0 && <p className="text-sm text-green-400">Aucun pic a corriger au-dessus du seuil.</p>}
                  </TabsContent>
                </Tabs>
              )}

              {/* Mode IA : boutons CLI */}
              {mode === "ia" && (
                <div className="flex flex-wrap gap-2">
                  <Button size="sm" variant="outline" onClick={() => exec("python -m backend.cli.lire_mesure")} disabled={running}><Search className="h-3.5 w-3.5 mr-1" />Lister</Button>
                  {paire.mesure_bas != null && <Button size="sm" variant="outline" onClick={() => exec(`python -m backend.cli.lire_mesure ${paire.mesure_bas} --phase --ir`)} disabled={running}><Waves className="h-3.5 w-3.5 mr-1" />{getEnc(paire.enceinte_bas)?.nom}</Button>}
                  {paire.mesure_haut != null && <Button size="sm" variant="outline" onClick={() => exec(`python -m backend.cli.lire_mesure ${paire.mesure_haut} --phase --ir`)} disabled={running}><Waves className="h-3.5 w-3.5 mr-1" />{getEnc(paire.enceinte_haut)?.nom}</Button>}
                  {paire.mesure_bas != null && paire.mesure_haut != null && <Button size="sm" onClick={() => exec(`python -m backend.cli.analyser ${paire.mesure_bas} ${paire.mesure_haut} --crossover ${paire.crossover_hz}`)} disabled={running}><Target className="h-3.5 w-3.5 mr-1" />Calage</Button>}
                  {paire.mesure_bas != null && <Button size="sm" variant="outline" onClick={() => exec(`python -m backend.cli.analyser ${paire.mesure_bas} --seuil 3`)} disabled={running}><SlidersHorizontal className="h-3.5 w-3.5 mr-1" />EQ</Button>}
                  <Button size="sm" variant="outline" onClick={() => exec(`python -m backend.cli.etat_dsp --host ${systeme.ip_dsp}`)} disabled={running}><Volume2 className="h-3.5 w-3.5 mr-1" />DSP</Button>
                </div>
              )}
            </>
          )}

          {!paireActive && systeme.paires.length > 0 && <p className="text-sm text-muted-foreground text-center py-8">Selectionne une paire ci-dessus pour commencer le calage.</p>}
          {systeme.paires.length === 0 && <p className="text-sm text-muted-foreground text-center py-8">Definis tes enceintes et paires dans l&apos;onglet Systeme d&apos;abord.</p>}
        </>
      )}

      {/* Preset Picker */}
      <PresetPicker
        open={presetPickerOpen}
        onClose={() => setPresetPickerOpen(false)}
        usedCanaux={systeme.enceintes.map((e) => e.canal_dsp)}
        onSelect={(preset: PresetEnceinte, canal: string) => {
          const id = `enc_${Date.now()}`;
          const s = {
            ...systeme,
            enceintes: [...systeme.enceintes, {
              id,
              nom: preset.nom,
              type: preset.type,
              canal_dsp: canal,
              hpf_hz: preset.hpf_hz,
              lpf_hz: preset.lpf_hz,
            }],
          };
          sauvegarder(s);
          log(`Enceinte ajoutee : ${preset.nom} → ${canal}`);
        }}
      />

      {/* Terminal + Journal */}
      <Tabs defaultValue="terminal">
        <TabsList>
          <TabsTrigger value="terminal" className="gap-1.5"><TerminalSquare className="h-3.5 w-3.5" />Terminal</TabsTrigger>
          <TabsTrigger value="journal" className="gap-1.5"><ScrollText className="h-3.5 w-3.5" />Journal{journal.length > 0 && <Badge variant="secondary" className="h-4 text-[10px] px-1 ml-1">{journal.length}</Badge>}</TabsTrigger>
        </TabsList>
        <TabsContent value="terminal" className="mt-2"><Terminal onCommandStart={() => setRunning(true)} onCommandEnd={() => setRunning(false)} /></TabsContent>
        <TabsContent value="journal" className="mt-2">
          <div className="border border-border rounded-lg bg-[#0d1117] p-3 font-mono text-xs leading-5 max-h-80 min-h-40 overflow-auto">
            {journal.length === 0 ? <span className="text-muted-foreground">Aucune action.</span> : journal.map((l, i) => <div key={i} className="text-muted-foreground">{l}</div>)}
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
