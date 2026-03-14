"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/status-badge";
import { rewStatus, rewMesures, rewFreqResponse } from "@/lib/api";
import { RefreshCw } from "lucide-react";

export default function MesuresPage() {
  const [connecte, setConnecte] = useState(false);
  const [mesures, setMesures] = useState<any[]>([]);
  const [selected, setSelected] = useState<number | null>(null);
  const [freqData, setFreqData] = useState<any>(null);

  const refresh = async () => {
    try {
      const s = await rewStatus();
      setConnecte(s.connecte);
      if (s.connecte) {
        const m = await rewMesures();
        setMesures(m);
      }
    } catch {
      setConnecte(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const loadMesure = async (idx: number) => {
    setSelected(idx);
    try {
      const data = await rewFreqResponse(idx);
      setFreqData(data);
    } catch {
      setFreqData(null);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold">Mesures</h2>
          <p className="text-muted-foreground text-sm">Mesures REW</p>
        </div>
        <div className="flex items-center gap-3">
          <StatusBadge connected={connecte} label={connecte ? "REW connecte" : "REW deconnecte"} />
          <Button size="sm" variant="outline" onClick={refresh}>
            <RefreshCw className="h-4 w-4 mr-1" />
            Rafraichir
          </Button>
        </div>
      </div>

      {!connecte ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>REW n&apos;est pas accessible.</p>
            <p className="text-sm mt-2">Lance REW et active l&apos;API dans Preferences &gt; API.</p>
          </CardContent>
        </Card>
      ) : mesures.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <p>Aucune mesure ouverte dans REW.</p>
            <p className="text-sm mt-2">Fais un sweep dans REW puis clique Rafraichir.</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
          <Card className="lg:col-span-1">
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                {mesures.length} mesure{mesures.length > 1 ? "s" : ""}
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-1">
              {mesures.map((m, i) => (
                <button
                  key={i}
                  onClick={() => loadMesure(i)}
                  className={`w-full text-left px-3 py-2 rounded-md text-sm transition-colors ${
                    selected === i
                      ? "bg-accent text-accent-foreground font-medium"
                      : "hover:bg-accent/50 text-muted-foreground"
                  }`}
                >
                  {m.name || m.title || `Mesure ${i}`}
                </button>
              ))}
            </CardContent>
          </Card>

          <Card className="lg:col-span-2">
            <CardHeader>
              <CardTitle className="text-sm font-medium">
                {selected !== null
                  ? mesures[selected]?.name || `Mesure ${selected}`
                  : "Selectionner une mesure"}
              </CardTitle>
            </CardHeader>
            <CardContent>
              {freqData ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="text-muted-foreground">Points :</span>{" "}
                      <span className="font-mono">{freqData.frequences?.length}</span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">Plage :</span>{" "}
                      <span className="font-mono">
                        {freqData.frequences?.[0]?.toFixed(1)} -{" "}
                        {freqData.frequences?.[freqData.frequences.length - 1]?.toFixed(0)} Hz
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">SPL min :</span>{" "}
                      <span className="font-mono">
                        {Math.min(...(freqData.magnitudes || [0])).toFixed(1)} dB
                      </span>
                    </div>
                    <div>
                      <span className="text-muted-foreground">SPL max :</span>{" "}
                      <span className="font-mono">
                        {Math.max(...(freqData.magnitudes || [0])).toFixed(1)} dB
                      </span>
                    </div>
                  </div>

                  <div className="text-xs text-muted-foreground">
                    Les courbes interactives arrivent dans une prochaine version.
                  </div>
                </div>
              ) : (
                <p className="text-muted-foreground text-sm">
                  Clique sur une mesure pour voir les details.
                </p>
              )}
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
}
