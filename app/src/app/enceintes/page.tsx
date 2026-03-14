"use client";

import { useState, useEffect } from "react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  getSysteme, saveSysteme, getPresets, addCustomPreset, deleteCustomPreset,
  type Systeme, type Enceinte, type PresetEnceinte,
} from "@/lib/api";
import { Plus, Trash2, Speaker, Save, Search, Edit3 } from "lucide-react";

const TYPES = [
  { value: "sub", label: "Sub", color: "bg-red-500/20 text-red-400 border-red-500/30" },
  { value: "top", label: "Top", color: "bg-blue-500/20 text-blue-400 border-blue-500/30" },
  { value: "low_mid", label: "Low-Mid", color: "bg-orange-500/20 text-orange-400 border-orange-500/30" },
  { value: "high", label: "HF", color: "bg-purple-500/20 text-purple-400 border-purple-500/30" },
  { value: "fill", label: "Fill", color: "bg-green-500/20 text-green-400 border-green-500/30" },
  { value: "delay", label: "Delay", color: "bg-cyan-500/20 text-cyan-400 border-cyan-500/30" },
  { value: "monitor", label: "Monitor", color: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30" },
];

const CANAUX = ["Out 1", "Out 2", "Out 3", "Out 4", "Out 5", "Out 6"];

const typeColor = (t: string) => TYPES.find((x) => x.value === t)?.color || "";
const typeLabel = (t: string) => TYPES.find((x) => x.value === t)?.label || t;

export default function EnceintesPage() {
  const [systeme, setSysteme] = useState<Systeme>({ nom: "", ip_dsp: "", port_dsp: 9761, enceintes: [], paires: [] });
  const [categories, setCategories] = useState<{ nom: string; enceintes: PresetEnceinte[] }[]>([]);
  const [search, setSearch] = useState("");
  const [tab, setTab] = useState("systeme");

  // Custom preset form
  const [showForm, setShowForm] = useState(false);
  const [form, setForm] = useState<PresetEnceinte>({ id: "", nom: "", type: "top", hp: "", bande: "", notes: "" });

  useEffect(() => {
    getSysteme().then(setSysteme).catch(() => {});
    getPresets().then((d) => setCategories(d.categories)).catch(() => {});
  }, []);

  const sauvegarder = async (s: Systeme) => {
    setSysteme(s);
    await saveSysteme(s).catch(() => {});
  };

  const ajouterDepuisPreset = (preset: PresetEnceinte) => {
    const usedCanaux = systeme.enceintes.map((e) => e.canal_dsp);
    const canal = CANAUX.find((c) => !usedCanaux.includes(c)) || CANAUX[0];
    const id = `enc_${Date.now()}`;
    sauvegarder({
      ...systeme,
      enceintes: [...systeme.enceintes, {
        id, nom: preset.nom, type: preset.type, canal_dsp: canal,
        hpf_hz: preset.hpf_hz, lpf_hz: preset.lpf_hz,
      }],
    });
  };

  const ajouterVide = () => {
    const usedCanaux = systeme.enceintes.map((e) => e.canal_dsp);
    const canal = CANAUX.find((c) => !usedCanaux.includes(c)) || CANAUX[0];
    const id = `enc_${Date.now()}`;
    sauvegarder({
      ...systeme,
      enceintes: [...systeme.enceintes, { id, nom: "", type: "top", canal_dsp: canal }],
    });
  };

  const majEnceinte = (id: string, updates: Partial<Enceinte>) => {
    sauvegarder({ ...systeme, enceintes: systeme.enceintes.map((e) => e.id === id ? { ...e, ...updates } : e) });
  };

  const suppEnceinte = (id: string) => {
    sauvegarder({
      ...systeme,
      enceintes: systeme.enceintes.filter((e) => e.id !== id),
      paires: systeme.paires.filter((p) => p.enceinte_bas !== id && p.enceinte_haut !== id),
    });
  };

  const sauvegarderCustom = async () => {
    const id = `custom_${Date.now()}`;
    try {
      await addCustomPreset({ ...form, id });
      getPresets().then((d) => setCategories(d.categories));
      setShowForm(false);
      setForm({ id: "", nom: "", type: "top", hp: "", bande: "", notes: "" });
    } catch { }
  };

  const supprimerCustom = async (id: string) => {
    await deleteCustomPreset(id).catch(() => {});
    getPresets().then((d) => setCategories(d.categories));
  };

  const filteredCats = categories.map((cat) => ({
    ...cat,
    enceintes: cat.enceintes.filter((e) =>
      !search || e.nom.toLowerCase().includes(search.toLowerCase()) || e.hp?.toLowerCase().includes(search.toLowerCase())
    ),
  })).filter((cat) => cat.enceintes.length > 0);

  return (
    <div className="space-y-4">
      <div>
        <h2 className="text-2xl font-bold">Enceintes</h2>
        <p className="text-muted-foreground text-sm">Bibliotheque et configuration du systeme</p>
      </div>

      <Tabs value={tab} onValueChange={setTab}>
        <TabsList>
          <TabsTrigger value="systeme" className="gap-1.5">
            <Speaker className="h-3.5 w-3.5" />Mon systeme ({systeme.enceintes.length})
          </TabsTrigger>
          <TabsTrigger value="presets" className="gap-1.5">
            <Search className="h-3.5 w-3.5" />Bibliotheque
          </TabsTrigger>
        </TabsList>

        {/* ===== MON SYSTEME ===== */}
        <TabsContent value="systeme" className="space-y-4 mt-3">
          <div className="flex gap-2">
            <Button size="sm" onClick={() => { setTab("presets"); }}><Plus className="h-3.5 w-3.5 mr-1" />Depuis la bibliotheque</Button>
            <Button size="sm" variant="outline" onClick={ajouterVide}><Plus className="h-3.5 w-3.5 mr-1" />Enceinte vide</Button>
          </div>

          {systeme.enceintes.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground">
                <Speaker className="h-8 w-8 mx-auto mb-3 opacity-30" />
                <p>Aucune enceinte dans le systeme.</p>
                <p className="text-sm mt-1">Ajoute des enceintes depuis la bibliotheque ou cree-en une vide.</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-2">
              {systeme.enceintes.map((e) => (
                <Card key={e.id}>
                  <CardContent className="pt-4">
                    <div className="flex items-start gap-3">
                      <div className="flex-1 grid grid-cols-2 md:grid-cols-5 gap-2">
                        <div>
                          <label className="text-[10px] text-muted-foreground">Nom</label>
                          <input type="text" value={e.nom} onChange={(ev) => majEnceinte(e.id, { nom: ev.target.value })}
                            placeholder="Ex: Sub L" className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground">Type</label>
                          <select value={e.type} onChange={(ev) => majEnceinte(e.id, { type: ev.target.value })}
                            className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm">
                            {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground">Canal DSP</label>
                          <select value={e.canal_dsp} onChange={(ev) => majEnceinte(e.id, { canal_dsp: ev.target.value })}
                            className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm">
                            {CANAUX.map((c) => <option key={c}>{c}</option>)}
                          </select>
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground">HPF (Hz)</label>
                          <input type="number" value={e.hpf_hz || ""} placeholder="—"
                            onChange={(ev) => majEnceinte(e.id, { hpf_hz: ev.target.value ? Number(ev.target.value) : null })}
                            className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                        </div>
                        <div>
                          <label className="text-[10px] text-muted-foreground">LPF (Hz)</label>
                          <input type="number" value={e.lpf_hz || ""} placeholder="—"
                            onChange={(ev) => majEnceinte(e.id, { lpf_hz: ev.target.value ? Number(ev.target.value) : null })}
                            className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                        </div>
                      </div>
                      <Badge variant="outline" className={`mt-5 text-[10px] ${typeColor(e.type)}`}>{typeLabel(e.type)}</Badge>
                      <Button size="sm" variant="ghost" className="mt-4" onClick={() => suppEnceinte(e.id)}>
                        <Trash2 className="h-3.5 w-3.5 text-red-400" />
                      </Button>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        {/* ===== BIBLIOTHEQUE ===== */}
        <TabsContent value="presets" className="space-y-4 mt-3">
          <div className="flex gap-2">
            <div className="relative flex-1">
              <Search className="absolute left-2.5 top-2.5 h-3.5 w-3.5 text-muted-foreground" />
              <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
                placeholder="Rechercher (nom, HP, type...)"
                className="w-full bg-muted border border-border rounded-md pl-8 pr-3 py-2 text-sm" />
            </div>
            <Button size="sm" variant="outline" onClick={() => setShowForm(!showForm)}>
              <Edit3 className="h-3.5 w-3.5 mr-1" />{showForm ? "Annuler" : "Creer un preset"}
            </Button>
          </div>

          {/* Formulaire creation custom */}
          {showForm && (
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm">Nouveau preset</CardTitle></CardHeader>
              <CardContent className="space-y-3">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-2">
                  <div>
                    <label className="text-[10px] text-muted-foreground">Nom</label>
                    <input type="text" value={form.nom} onChange={(e) => setForm({ ...form, nom: e.target.value })}
                      placeholder="Ex: Mon sub custom" className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Type</label>
                    <select value={form.type} onChange={(e) => setForm({ ...form, type: e.target.value })}
                      className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm">
                      {TYPES.map((t) => <option key={t.value} value={t.value}>{t.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Haut-parleur(s)</label>
                    <input type="text" value={form.hp} onChange={(e) => setForm({ ...form, hp: e.target.value })}
                      placeholder="Ex: 2x B&C 18SW115" className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Bande passante</label>
                    <input type="text" value={form.bande} onChange={(e) => setForm({ ...form, bande: e.target.value })}
                      placeholder="Ex: 30-120 Hz" className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                  </div>
                </div>
                <div className="grid grid-cols-3 gap-2">
                  <div>
                    <label className="text-[10px] text-muted-foreground">HPF (Hz)</label>
                    <input type="number" value={form.hpf_hz || ""} onChange={(e) => setForm({ ...form, hpf_hz: e.target.value ? Number(e.target.value) : null })}
                      className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">LPF (Hz)</label>
                    <input type="number" value={form.lpf_hz || ""} onChange={(e) => setForm({ ...form, lpf_hz: e.target.value ? Number(e.target.value) : null })}
                      className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm font-mono" />
                  </div>
                  <div>
                    <label className="text-[10px] text-muted-foreground">Notes</label>
                    <input type="text" value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                      className="w-full bg-muted border border-border rounded px-2 py-1.5 text-sm" />
                  </div>
                </div>
                <Button size="sm" onClick={sauvegarderCustom} disabled={!form.nom}>
                  <Save className="h-3.5 w-3.5 mr-1" />Sauvegarder
                </Button>
              </CardContent>
            </Card>
          )}

          {/* Liste des presets */}
          <ScrollArea className="max-h-[60vh]">
            {filteredCats.map((cat) => (
              <div key={cat.nom} className="mb-6">
                <div className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-2">{cat.nom}</div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {cat.enceintes.map((enc) => (
                    <Card key={enc.id} className="hover:border-primary/30 transition-colors cursor-pointer" onClick={() => ajouterDepuisPreset(enc)}>
                      <CardContent className="p-3">
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-sm font-medium">{enc.nom}</span>
                          <div className="flex items-center gap-1.5">
                            <Badge variant="outline" className={`text-[10px] ${typeColor(enc.type)}`}>{typeLabel(enc.type)}</Badge>
                            {cat.nom === "Mes enceintes" && (
                              <Button size="sm" variant="ghost" className="h-5 w-5 p-0" onClick={(e) => { e.stopPropagation(); supprimerCustom(enc.id); }}>
                                <Trash2 className="h-3 w-3 text-red-400" />
                              </Button>
                            )}
                          </div>
                        </div>
                        <div className="text-xs text-muted-foreground">{enc.hp}</div>
                        <div className="flex gap-3 mt-1 text-[10px] text-muted-foreground">
                          {enc.bande && <span>{enc.bande}</span>}
                          {enc.hpf_hz && <span>HPF: {enc.hpf_hz} Hz</span>}
                          {enc.lpf_hz && <span>LPF: {enc.lpf_hz} Hz</span>}
                        </div>
                        {enc.notes && <div className="text-[10px] text-muted-foreground/70 mt-1">{enc.notes}</div>}
                      </CardContent>
                    </Card>
                  ))}
                </div>
              </div>
            ))}
          </ScrollArea>
        </TabsContent>
      </Tabs>
    </div>
  );
}
