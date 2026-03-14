"use client";

import { useEffect, useState } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { StatusBadge } from "@/components/status-badge";
import { rewStatus, dspStatus, dspMetres } from "@/lib/api";
import { Activity, Radio, Volume2, Clock } from "lucide-react";

export default function Dashboard() {
  const [rew, setRew] = useState({ connecte: false, url: "" });
  const [dsp, setDsp] = useState({ connecte: false, modele: null as string | null });
  const [metres, setMetres] = useState<Record<string, number>>({});

  useEffect(() => {
    const refresh = () => {
      rewStatus().then(setRew).catch(() => setRew({ connecte: false, url: "" }));
      dspStatus().then((d) => {
        setDsp(d);
        if (d.connecte) dspMetres().then(setMetres).catch(() => {});
      }).catch(() => setDsp({ connecte: false, modele: null }));
    };
    refresh();
    const id = setInterval(refresh, 2000);
    return () => clearInterval(id);
  }, []);

  const dbFromLinear = (v: number) =>
    v > 0.0001 ? (20 * Math.log10(v)).toFixed(1) : "-inf";

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Dashboard</h2>
        <p className="text-muted-foreground text-sm">Vue d&apos;ensemble du systeme</p>
      </div>

      <div className="flex gap-3">
        <StatusBadge connected={rew.connecte} label={rew.connecte ? "REW connecte" : "REW deconnecte"} />
        <StatusBadge
          connected={dsp.connecte}
          label={dsp.connecte ? `DSP ${dsp.modele}` : "DSP deconnecte"}
        />
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">REW</CardTitle>
            <Activity className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {rew.connecte ? "En ligne" : "Hors ligne"}
            </div>
            <p className="text-xs text-muted-foreground">{rew.url || "localhost:4735"}</p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">DSP</CardTitle>
            <Radio className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dsp.connecte ? dsp.modele : "Deconnecte"}
            </div>
            <p className="text-xs text-muted-foreground">
              {dsp.connecte ? "TCP 9761" : "Aucune connexion"}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Canaux</CardTitle>
            <Volume2 className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">
              {dsp.connecte ? Object.keys(metres).length : "\u2014"}
            </div>
            <p className="text-xs text-muted-foreground">
              {dsp.connecte ? "2 in / 6 out" : ""}
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex flex-row items-center justify-between pb-2">
            <CardTitle className="text-sm font-medium">Mode</CardTitle>
            <Clock className="h-4 w-4 text-muted-foreground" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold">Script</div>
            <p className="text-xs text-muted-foreground">Algorithmes fixes</p>
          </CardContent>
        </Card>
      </div>

      {dsp.connecte && Object.keys(metres).length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Metres temps reel</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {Object.entries(metres).map(([canal, niveau]) => {
                const db = niveau > 0.0001 ? 20 * Math.log10(niveau) : -60;
                const pct = Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
                return (
                  <div key={canal} className="flex items-center gap-3">
                    <span className="text-xs w-12 text-right font-mono text-muted-foreground">
                      {canal}
                    </span>
                    <div className="flex-1 h-3 bg-muted rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full transition-all duration-200"
                        style={{
                          width: `${pct}%`,
                          backgroundColor:
                            db > -6 ? "#ef4444" : db > -18 ? "#f59e0b" : "#22c55e",
                        }}
                      />
                    </div>
                    <span className="text-xs w-16 font-mono">
                      {dbFromLinear(niveau)} dB
                    </span>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
