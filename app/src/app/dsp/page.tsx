"use client";

import { useEffect, useState, useCallback } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Separator } from "@/components/ui/separator";
import { Switch } from "@/components/ui/switch";
import { StatusBadge } from "@/components/status-badge";
import {
  dspStatus,
  dspConnect,
  dspDisconnect,
  dspEtat,
  dspSetGain,
  dspSetMute,
  dspMetres,
} from "@/lib/api";
import { Plug, Unplug } from "lucide-react";

export default function DSPPage() {
  const [connecte, setConnecte] = useState(false);
  const [modele, setModele] = useState("");
  const [host, setHost] = useState("127.0.0.1");
  const [etat, setEtat] = useState<any>(null);
  const [metres, setMetres] = useState<Record<string, number>>({});
  const [loading, setLoading] = useState(false);

  const refresh = useCallback(() => {
    dspStatus().then((d) => {
      setConnecte(d.connecte);
      setModele(d.modele || "");
      if (d.connecte) {
        dspEtat().then(setEtat).catch(() => {});
        dspMetres().then(setMetres).catch(() => {});
      }
    }).catch(() => setConnecte(false));
  }, []);

  useEffect(() => {
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, [refresh]);

  const handleConnect = async () => {
    setLoading(true);
    try {
      const r = await dspConnect(host);
      setConnecte(r.connecte);
      setModele(r.modele);
      refresh();
    } catch {
      alert("Impossible de se connecter au DSP");
    }
    setLoading(false);
  };

  const handleDisconnect = async () => {
    await dspDisconnect();
    setConnecte(false);
    setEtat(null);
    setMetres({});
  };

  const handleGain = async (canal: string, delta: number) => {
    const current = etat?.canaux?.[canal]?.gain_db ?? 0;
    await dspSetGain(canal, current + delta);
    refresh();
  };

  const handleMute = async (canal: string, mute: boolean) => {
    await dspSetMute(canal, mute);
    refresh();
  };

  const dbFromLinear = (v: number) =>
    v > 0.0001 ? (20 * Math.log10(v)).toFixed(1) : "-inf";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Controle DSP</h2>
        <p className="text-muted-foreground text-sm">Processeur t.racks</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Connexion</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={host}
              onChange={(e) => setHost(e.target.value)}
              className="bg-muted border border-border rounded-md px-3 py-1.5 text-sm font-mono w-48"
              placeholder="IP du DSP"
            />
            <span className="text-sm text-muted-foreground">: 9761</span>
            {!connecte ? (
              <Button size="sm" onClick={handleConnect} disabled={loading}>
                <Plug className="h-4 w-4 mr-1" />
                Connecter
              </Button>
            ) : (
              <Button size="sm" variant="outline" onClick={handleDisconnect}>
                <Unplug className="h-4 w-4 mr-1" />
                Deconnecter
              </Button>
            )}
            <StatusBadge
              connected={connecte}
              label={connecte ? modele : "Deconnecte"}
            />
          </div>
        </CardContent>
      </Card>

      {connecte && etat?.canaux && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Canaux</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {Object.entries(etat.canaux as Record<string, any>).map(
                ([canal, info]: [string, any]) => {
                  const niveau = metres[canal] ?? 0;
                  const db = niveau > 0.0001 ? 20 * Math.log10(niveau) : -60;
                  const pct = Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
                  return (
                    <div key={canal} className="flex items-center gap-3 py-1">
                      <span className="text-xs w-12 text-right font-mono font-medium">
                        {canal}
                      </span>

                      <div className="w-20 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full transition-all"
                          style={{
                            width: `${pct}%`,
                            backgroundColor: db > -6 ? "#ef4444" : db > -18 ? "#f59e0b" : "#22c55e",
                          }}
                        />
                      </div>

                      <div className="flex items-center gap-1">
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 w-6 p-0 text-xs"
                          onClick={() => handleGain(canal, -1)}
                        >
                          -
                        </Button>
                        <span className="text-xs font-mono w-14 text-center">
                          {info.gain_db?.toFixed(1) ?? "0.0"} dB
                        </span>
                        <Button
                          variant="outline"
                          size="sm"
                          className="h-6 w-6 p-0 text-xs"
                          onClick={() => handleGain(canal, 1)}
                        >
                          +
                        </Button>
                      </div>

                      <div className="flex items-center gap-1.5">
                        <Switch
                          checked={info.mute ?? false}
                          onCheckedChange={(m) => handleMute(canal, m)}
                        />
                        <span className="text-[10px] text-muted-foreground w-8">
                          {info.mute ? "MUTE" : ""}
                        </span>
                      </div>

                      <span className="text-[10px] font-mono text-muted-foreground w-12">
                        {dbFromLinear(niveau)} dB
                      </span>
                    </div>
                  );
                }
              )}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
