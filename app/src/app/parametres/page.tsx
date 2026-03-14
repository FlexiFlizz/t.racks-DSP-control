"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

export default function ParametresPage() {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Parametres</h2>
        <p className="text-muted-foreground text-sm">Configuration de l&apos;application</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">REW</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Adresse</span>
            <span className="font-mono">localhost:4735</span>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Licence Pro</span>
            <span>Non (mesures manuelles)</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">DSP t.racks</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">Protocole</span>
            <span className="font-mono">TCP port 9761</span>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Modeles supportes</span>
            <span>DSP 206, 408, 306, 204</span>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Simulateur</span>
            <span className="font-mono text-xs">python tools/simulateur_dsp206.py</span>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle className="text-sm font-medium">Backend</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3 text-sm">
          <div className="flex justify-between">
            <span className="text-muted-foreground">API</span>
            <span className="font-mono">http://127.0.0.1:8765</span>
          </div>
          <Separator />
          <div className="flex justify-between">
            <span className="text-muted-foreground">Version</span>
            <span>0.1.0</span>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
