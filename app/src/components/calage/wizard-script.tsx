"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import { StatusBadge } from "@/components/status-badge";
import {
  rewStatus,
  rewMesures,
  dspStatus,
  dspConnect,
  calageDelay,
  calageEQ,
  dspSetGain,
  dspSetDelay,
  dspSetMute,
} from "@/lib/api";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  AlertTriangle,
  Play,
  RefreshCw,
  Loader2,
} from "lucide-react";

type Etape = "config" | "connexion" | "mesures" | "analyse" | "application" | "verification";

const ETAPES: { id: Etape; label: string }[] = [
  { id: "config", label: "Configuration" },
  { id: "connexion", label: "Connexion" },
  { id: "mesures", label: "Mesures" },
  { id: "analyse", label: "Analyse" },
  { id: "application", label: "Application" },
  { id: "verification", label: "Verification" },
];

export function WizardScript({ onBack }: { onBack: () => void }) {
  const [etape, setEtape] = useState<Etape>("config");
  const [rewOk, setRewOk] = useState(false);
  const [dspOk, setDspOk] = useState(false);
  const [mesures, setMesures] = useState<any[]>([]);
  const [loading, setLoading] = useState(false);
  const [logs, setLogs] = useState<string[]>([]);

  // Config
  const [type, setType] = useState("sub_top");
  const [crossover, setCrossover] = useState(120);
  const [mesureA, setMesureA] = useState(0);
  const [mesureB, setMesureB] = useState(1);
  const [canalDelay, setCanalDelay] = useState("Out 1");
  const [canalEQ, setCanalEQ] = useState("Out 1");
  const [dspHost, setDspHost] = useState("127.0.0.1");

  // Resultats
  const [resultatDelay, setResultatDelay] = useState<any>(null);
  const [resultatEQ, setResultatEQ] = useState<any>(null);

  const log = (msg: string) => setLogs((l) => [...l, `[${new Date().toLocaleTimeString()}] ${msg}`]);

  const etapeIdx = ETAPES.findIndex((e) => e.id === etape);

  const refreshConnexions = async () => {
    try {
      const r = await rewStatus();
      setRewOk(r.connecte);
    } catch {
      setRewOk(false);
    }
    try {
      const d = await dspStatus();
      setDspOk(d.connecte);
    } catch {
      setDspOk(false);
    }
  };

  const refreshMesures = async () => {
    try {
      const m = await rewMesures();
      setMesures(m);
      log(`${m.length} mesure(s) trouvee(s) dans REW`);
    } catch {
      log("Impossible de lire les mesures REW");
    }
  };

  useEffect(() => {
    refreshConnexions();
  }, [etape]);

  const connecterDSP = async () => {
    setLoading(true);
    try {
      await dspConnect(dspHost);
      setDspOk(true);
      log(`DSP connecte sur ${dspHost}:9761`);
    } catch {
      log("Echec connexion DSP");
    }
    setLoading(false);
  };

  const lancerAnalyse = async () => {
    setLoading(true);
    setResultatDelay(null);
    setResultatEQ(null);
    log("Lancement de l'analyse...");

    try {
      // Analyse delay
      log(`Calcul delay : mesure ${mesureA} vs ${mesureB} @ ${crossover} Hz`);
      const rd = await calageDelay({
        index_mesure_a: mesureA,
        index_mesure_b: mesureB,
        freq_crossover: crossover,
        canal_delay: canalDelay,
        appliquer: false,
      });
      setResultatDelay(rd);
      rd.messages?.forEach((m: string) => log(m));

      // Analyse EQ
      log(`Calcul EQ correctif pour mesure ${mesureA}...`);
      const re = await calageEQ({
        index_mesure: mesureA,
        canal_dsp: canalEQ,
        appliquer: false,
      });
      setResultatEQ(re);
      re.messages?.forEach((m: string) => log(m));

      log("Analyse terminee.");
    } catch (e: any) {
      log(`ERREUR : ${e.message}`);
    }
    setLoading(false);
  };

  const appliquerCorrections = async () => {
    setLoading(true);
    try {
      if (resultatDelay?.delay_ms > 0) {
        log(`Application delay ${resultatDelay.delay_ms} ms sur ${canalDelay}`);
        await dspSetDelay(canalDelay, resultatDelay.delay_ms);
      }

      if (resultatEQ?.filtres?.length > 0) {
        log(`Application de ${resultatEQ.filtres.length} filtres EQ sur ${canalEQ}`);
        // Appeler le backend pour appliquer l'EQ
        await calageEQ({
          index_mesure: mesureA,
          canal_dsp: canalEQ,
          appliquer: true,
        });
      }

      log("Corrections appliquees sur le DSP.");
    } catch (e: any) {
      log(`ERREUR application : ${e.message}`);
    }
    setLoading(false);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="h-4 w-4 mr-1" />
          Retour
        </Button>
        <div>
          <h2 className="text-2xl font-bold">Mode Script</h2>
          <p className="text-muted-foreground text-sm">Calage algorithmique</p>
        </div>
      </div>

      {/* Stepper */}
      <div className="flex gap-1">
        {ETAPES.map((e, i) => (
          <button
            key={e.id}
            onClick={() => setEtape(e.id)}
            className={`flex-1 py-2 px-2 text-xs rounded-md transition-colors ${
              i === etapeIdx
                ? "bg-primary text-primary-foreground font-medium"
                : i < etapeIdx
                ? "bg-accent text-accent-foreground"
                : "bg-muted text-muted-foreground"
            }`}
          >
            {e.label}
          </button>
        ))}
      </div>

      {/* Contenu par etape */}
      {etape === "config" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Configuration du systeme</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div>
              <label className="text-sm text-muted-foreground">Type de systeme</label>
              <select
                value={type}
                onChange={(e) => setType(e.target.value)}
                className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
              >
                <option value="sub_top">Sub + Top (2 voies)</option>
                <option value="3voies">3 voies</option>
                <option value="multi_zone">Multi-zones (fills, delays)</option>
              </select>
            </div>
            <div>
              <label className="text-sm text-muted-foreground">Frequence de crossover (Hz)</label>
              <input
                type="number"
                value={crossover}
                onChange={(e) => setCrossover(Number(e.target.value))}
                className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm font-mono"
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="text-sm text-muted-foreground">Canal delay DSP</label>
                <select
                  value={canalDelay}
                  onChange={(e) => setCanalDelay(e.target.value)}
                  className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
                >
                  {["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-sm text-muted-foreground">Canal EQ DSP</label>
                <select
                  value={canalEQ}
                  onChange={(e) => setCanalEQ(e.target.value)}
                  className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
                >
                  {["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"].map((c) => (
                    <option key={c}>{c}</option>
                  ))}
                </select>
              </div>
            </div>
            <Button onClick={() => setEtape("connexion")}>
              Suivant <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
          </CardContent>
        </Card>
      )}

      {etape === "connexion" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Connexion REW + DSP</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-3">
                <StatusBadge connected={rewOk} label={rewOk ? "REW connecte" : "REW deconnecte"} />
                <span className="text-xs text-muted-foreground">localhost:4735</span>
              </div>
              <Button size="sm" variant="outline" onClick={refreshConnexions}>
                <RefreshCw className="h-4 w-4" />
              </Button>
            </div>
            {!rewOk && (
              <p className="text-xs text-yellow-400">
                Lance REW et active l&apos;API dans Preferences &gt; API
              </p>
            )}
            <Separator />
            <div className="flex items-center gap-3">
              <StatusBadge connected={dspOk} label={dspOk ? "DSP connecte" : "DSP deconnecte"} />
              <input
                type="text"
                value={dspHost}
                onChange={(e) => setDspHost(e.target.value)}
                className="bg-muted border border-border rounded-md px-3 py-1 text-sm font-mono w-40"
              />
              {!dspOk && (
                <Button size="sm" onClick={connecterDSP} disabled={loading}>
                  Connecter
                </Button>
              )}
            </div>
            <Button onClick={() => setEtape("mesures")} disabled={!rewOk || !dspOk}>
              Suivant <ArrowRight className="h-4 w-4 ml-1" />
            </Button>
            {(!rewOk || !dspOk) && (
              <p className="text-xs text-muted-foreground">
                Les deux doivent etre connectes pour continuer.
              </p>
            )}
          </CardContent>
        </Card>
      )}

      {etape === "mesures" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Selection des mesures</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <Button size="sm" variant="outline" onClick={refreshMesures}>
              <RefreshCw className="h-4 w-4 mr-1" />
              Detecter les mesures REW
            </Button>

            {mesures.length > 0 ? (
              <>
                <div className="space-y-1 max-h-40 overflow-auto">
                  {mesures.map((m, i) => (
                    <div key={i} className="text-sm font-mono px-2 py-1 bg-muted rounded">
                      [{i}] {m.name || m.title || `Mesure ${i}`}
                    </div>
                  ))}
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="text-sm text-muted-foreground">Mesure A (sub / source 1)</label>
                    <select
                      value={mesureA}
                      onChange={(e) => setMesureA(Number(e.target.value))}
                      className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
                    >
                      {mesures.map((m, i) => (
                        <option key={i} value={i}>
                          [{i}] {m.name || `Mesure ${i}`}
                        </option>
                      ))}
                    </select>
                  </div>
                  <div>
                    <label className="text-sm text-muted-foreground">Mesure B (top / source 2)</label>
                    <select
                      value={mesureB}
                      onChange={(e) => setMesureB(Number(e.target.value))}
                      className="w-full mt-1 bg-muted border border-border rounded-md px-3 py-2 text-sm"
                    >
                      {mesures.map((m, i) => (
                        <option key={i} value={i}>
                          [{i}] {m.name || `Mesure ${i}`}
                        </option>
                      ))}
                    </select>
                  </div>
                </div>
                <Button onClick={() => setEtape("analyse")}>
                  Lancer l&apos;analyse <ArrowRight className="h-4 w-4 ml-1" />
                </Button>
              </>
            ) : (
              <div className="text-sm text-muted-foreground space-y-2">
                <p>Fais tes sweeps dans REW puis clique &quot;Detecter&quot;.</p>
                <ol className="list-decimal pl-4 space-y-1 text-xs">
                  <li>Dans REW, mesure le sub seul (sweep)</li>
                  <li>Mesure le top seul (sweep)</li>
                  <li>Clique &quot;Detecter les mesures REW&quot; ci-dessus</li>
                </ol>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {etape === "analyse" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Analyse</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm space-y-1">
              <p>Mesure A : <span className="font-mono">[{mesureA}]</span></p>
              <p>Mesure B : <span className="font-mono">[{mesureB}]</span></p>
              <p>Crossover : <span className="font-mono">{crossover} Hz</span></p>
            </div>

            <Button onClick={lancerAnalyse} disabled={loading}>
              {loading ? (
                <Loader2 className="h-4 w-4 mr-1 animate-spin" />
              ) : (
                <Play className="h-4 w-4 mr-1" />
              )}
              {loading ? "Analyse en cours..." : "Lancer l'analyse"}
            </Button>

            {resultatDelay && (
              <div className="space-y-3">
                <Separator />
                <h3 className="text-sm font-medium">Resultats delay</h3>
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="bg-muted p-2 rounded">
                    <span className="text-muted-foreground">Delay :</span>{" "}
                    <span className="font-mono font-bold">{resultatDelay.delay_ms?.toFixed(2)} ms</span>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <span className="text-muted-foreground">Appliquer sur :</span>{" "}
                    <span className="font-mono">{resultatDelay.appliquer_sur}</span>
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <span className="text-muted-foreground">Polarite :</span>{" "}
                    {resultatDelay.inverser_polarite ? (
                      <Badge variant="destructive" className="text-xs">INVERSER</Badge>
                    ) : (
                      <Badge variant="outline" className="text-xs border-green-500 text-green-400">OK</Badge>
                    )}
                  </div>
                  <div className="bg-muted p-2 rounded">
                    <span className="text-muted-foreground">Coherence :</span>{" "}
                    <span className="font-mono">{(resultatDelay.coherence_phase * 100).toFixed(0)}%</span>
                  </div>
                </div>
              </div>
            )}

            {resultatEQ && resultatEQ.filtres?.length > 0 && (
              <div className="space-y-3">
                <Separator />
                <h3 className="text-sm font-medium">Filtres EQ correctifs (soustractifs)</h3>
                <div className="text-xs font-mono bg-muted p-3 rounded space-y-1">
                  <div className="flex gap-4 text-muted-foreground mb-1">
                    <span className="w-8">Band</span>
                    <span className="w-20">Freq</span>
                    <span className="w-16">Gain</span>
                    <span className="w-12">Q</span>
                  </div>
                  {resultatEQ.filtres.map((f: any, i: number) => (
                    <div key={i} className="flex gap-4">
                      <span className="w-8">{i}</span>
                      <span className="w-20">{f.frequence_hz?.toFixed(0)} Hz</span>
                      <span className="w-16 text-red-400">{f.gain_db?.toFixed(1)} dB</span>
                      <span className="w-12">{f.q?.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {(resultatDelay || resultatEQ) && (
              <Button onClick={() => setEtape("application")}>
                Appliquer les corrections <ArrowRight className="h-4 w-4 ml-1" />
              </Button>
            )}
          </CardContent>
        </Card>
      )}

      {etape === "application" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Application des corrections</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="text-sm space-y-2">
              {resultatDelay?.delay_ms > 0 && (
                <div className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green-400" />
                  Delay {resultatDelay.delay_ms?.toFixed(2)} ms sur {canalDelay}
                </div>
              )}
              {resultatDelay?.inverser_polarite && (
                <div className="flex items-center gap-2">
                  <AlertTriangle className="h-4 w-4 text-yellow-400" />
                  Polarite a inverser (action manuelle sur le DSP)
                </div>
              )}
              {resultatEQ?.filtres?.length > 0 && (
                <div className="flex items-center gap-2">
                  <Check className="h-4 w-4 text-green-400" />
                  {resultatEQ.filtres.length} filtres EQ sur {canalEQ}
                </div>
              )}
            </div>

            <div className="flex gap-3">
              <Button onClick={appliquerCorrections} disabled={loading}>
                {loading ? (
                  <Loader2 className="h-4 w-4 mr-1 animate-spin" />
                ) : (
                  <Play className="h-4 w-4 mr-1" />
                )}
                Appliquer sur le DSP
              </Button>
              <Button variant="outline" onClick={() => setEtape("verification")}>
                Passer a la verification
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {etape === "verification" && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm">Verification</CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              Fais une nouvelle mesure dans REW pour verifier le resultat.
            </p>
            <ol className="list-decimal pl-4 text-sm space-y-1 text-muted-foreground">
              <li>Mesure le systeme complet (sub + top ensemble)</li>
              <li>Compare avec la mesure d&apos;avant</li>
              <li>Si besoin, relance le calage</li>
            </ol>
            <div className="flex gap-3">
              <Button variant="outline" onClick={() => setEtape("analyse")}>
                Relancer l&apos;analyse
              </Button>
              <Button variant="outline" onClick={onBack}>
                Terminer
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Log */}
      {logs.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">Journal</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="max-h-48 overflow-auto text-xs font-mono space-y-0.5 bg-muted p-3 rounded">
              {logs.map((l, i) => (
                <div key={i} className="text-muted-foreground">{l}</div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
