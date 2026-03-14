"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { getPresets, type PresetEnceinte, type Enceinte } from "@/lib/api";
import { Plus, X, Search, Speaker } from "lucide-react";

interface PresetPickerProps {
  open: boolean;
  onClose: () => void;
  onSelect: (preset: PresetEnceinte, canal: string) => void;
  usedCanaux: string[];
}

const CANAUX = ["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"];

const TYPE_COLORS: Record<string, string> = {
  sub: "bg-red-500/20 text-red-400 border-red-500/30",
  top: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  low_mid: "bg-orange-500/20 text-orange-400 border-orange-500/30",
  high: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  fill: "bg-green-500/20 text-green-400 border-green-500/30",
  delay: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30",
  monitor: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
};

export function PresetPicker({ open, onClose, onSelect, usedCanaux }: PresetPickerProps) {
  const [categories, setCategories] = useState<{ nom: string; enceintes: PresetEnceinte[] }[]>([]);
  const [search, setSearch] = useState("");
  const [selectedPreset, setSelectedPreset] = useState<PresetEnceinte | null>(null);
  const [canal, setCanal] = useState("");

  useEffect(() => {
    if (open) {
      getPresets().then((d) => setCategories(d.categories)).catch(() => {});
      // Trouver le premier canal libre
      const libre = CANAUX.find((c) => !usedCanaux.includes(c));
      setCanal(libre || CANAUX[0]);
    }
  }, [open, usedCanaux]);

  if (!open) return null;

  const filteredCats = categories.map((cat) => ({
    ...cat,
    enceintes: cat.enceintes.filter(
      (e) =>
        !search ||
        e.nom.toLowerCase().includes(search.toLowerCase()) ||
        e.hp.toLowerCase().includes(search.toLowerCase()) ||
        e.type.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter((cat) => cat.enceintes.length > 0);

  return (
    <div className="fixed inset-0 bg-black/60 z-50 flex items-center justify-center p-4" onClick={onClose}>
      <Card className="w-full max-w-2xl max-h-[80vh] flex flex-col" onClick={(e) => e.stopPropagation()}>
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm font-medium flex items-center gap-2">
              <Speaker className="h-4 w-4" />
              Choisir une enceinte
            </CardTitle>
            <Button size="sm" variant="ghost" onClick={onClose}><X className="h-4 w-4" /></Button>
          </div>
          <div className="relative mt-2">
            <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-muted-foreground" />
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Rechercher (nom, HP, type...)"
              className="w-full bg-muted border border-border rounded-md pl-8 pr-3 py-1.5 text-sm"
              autoFocus
            />
          </div>
        </CardHeader>
        <CardContent className="flex-1 overflow-hidden p-0">
          <ScrollArea className="h-[50vh] px-4">
            {filteredCats.map((cat) => (
              <div key={cat.nom} className="mb-4">
                <div className="text-[11px] font-medium text-muted-foreground uppercase tracking-wider mb-2">{cat.nom}</div>
                <div className="space-y-1.5">
                  {cat.enceintes.map((enc) => (
                    <button
                      key={enc.id}
                      onClick={() => setSelectedPreset(enc)}
                      className={`w-full text-left p-3 rounded-lg border transition-colors ${
                        selectedPreset?.id === enc.id
                          ? "border-primary bg-primary/5"
                          : "border-border hover:border-primary/30 hover:bg-muted/50"
                      }`}
                    >
                      <div className="flex items-center justify-between">
                        <span className="text-sm font-medium">{enc.nom}</span>
                        <Badge variant="outline" className={`text-[10px] ${TYPE_COLORS[enc.type] || ""}`}>
                          {enc.type}
                        </Badge>
                      </div>
                      <div className="text-xs text-muted-foreground mt-1">{enc.hp}</div>
                      <div className="flex gap-3 mt-1 text-[10px] text-muted-foreground">
                        <span>{enc.bande}</span>
                        {enc.hpf_hz && <span>HPF: {enc.hpf_hz} Hz</span>}
                        {enc.lpf_hz && <span>LPF: {enc.lpf_hz} Hz</span>}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </ScrollArea>
        </CardContent>

        {selectedPreset && (
          <div className="border-t border-border p-4">
            <div className="flex items-center gap-3">
              <div className="flex-1">
                <div className="text-sm font-medium">{selectedPreset.nom}</div>
                <div className="text-xs text-muted-foreground">{selectedPreset.hp}</div>
              </div>
              <select
                value={canal}
                onChange={(e) => setCanal(e.target.value)}
                className="bg-muted border border-border rounded px-2 py-1.5 text-sm w-24"
              >
                {CANAUX.map((c) => (
                  <option key={c} disabled={usedCanaux.includes(c)}>
                    {c} {usedCanaux.includes(c) ? "(pris)" : ""}
                  </option>
                ))}
              </select>
              <Button
                size="sm"
                onClick={() => {
                  onSelect(selectedPreset, canal);
                  onClose();
                }}
              >
                <Plus className="h-3.5 w-3.5 mr-1" />
                Ajouter
              </Button>
            </div>
          </div>
        )}
      </Card>
    </div>
  );
}
