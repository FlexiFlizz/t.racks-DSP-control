const API_BASE = "http://127.0.0.1:8765";

async function fetchApi<T>(endpoint: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${endpoint}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options?.headers },
  });
  if (!res.ok) throw new Error(`API error ${res.status}: ${await res.text()}`);
  return res.json();
}

// -- REW --
export const rewStatus = () => fetchApi<{ connecte: boolean; url: string }>("/rew/status");
export const rewMesures = () => fetchApi<any[]>("/rew/mesures");
export const rewFreqResponse = (id: number, smoothing = "1/12") =>
  fetchApi<{ frequences: number[]; magnitudes: number[]; phases: number[] }>(
    `/rew/mesures/${id}/freq?smoothing=${smoothing}`
  );

// -- DSP --
export const dspStatus = () =>
  fetchApi<{ connecte: boolean; modele: string | null }>("/dsp/status");
export const dspConnect = (host: string, port = 9761) =>
  fetchApi<{ connecte: boolean; modele: string; canaux: Record<string, number> }>(
    "/dsp/connect",
    { method: "POST", body: JSON.stringify({ host, port }) }
  );
export const dspDisconnect = () =>
  fetchApi("/dsp/disconnect", { method: "POST" });
export const dspCanaux = () =>
  fetchApi<{ entrees: Record<string, number>; sorties: Record<string, number> }>("/dsp/canaux");
export const dspEtat = () => fetchApi<any>("/dsp/etat");
export const dspSetGain = (canal: string, db: number) =>
  fetchApi("/dsp/gain", { method: "POST", body: JSON.stringify({ canal, db }) });
export const dspSetMute = (canal: string, mute: boolean) =>
  fetchApi("/dsp/mute", { method: "POST", body: JSON.stringify({ canal, mute }) });
export const dspSetDelay = (canal: string, delay_ms: number) =>
  fetchApi("/dsp/delay", { method: "POST", body: JSON.stringify({ canal, delay_ms }) });
export const dspMetres = () => fetchApi<Record<string, number>>("/dsp/metres");

// -- REW direct (proxy vers REW API) --
export const rewSelectMesure = (index: number) =>
  fetchApi("/rew/select", { method: "POST", body: JSON.stringify({ index }) });
export const rewDeleteMesure = (id: number) =>
  fetchApi(`/rew/mesures/${id}`, { method: "DELETE" });
export const rewGroupDelay = (id: number) =>
  fetchApi<any>(`/rew/mesures/${id}/group-delay`);
export const rewIR = (id: number) =>
  fetchApi<any>(`/rew/mesures/${id}/ir`);
export const rewEQCommands = (id: number) =>
  fetchApi<any>(`/rew/mesures/${id}/eq-commands`);
export const rewEQMatch = (id: number, command: string) =>
  fetchApi<any>(`/rew/mesures/${id}/eq-command`, {
    method: "POST",
    body: JSON.stringify({ command }),
  });
export const rewFilters = (id: number) =>
  fetchApi<any>(`/rew/mesures/${id}/filters`);
export const rewGeneratorStart = () =>
  fetchApi("/rew/generator/start", { method: "POST" });
export const rewGeneratorStop = () =>
  fetchApi("/rew/generator/stop", { method: "POST" });

// -- Systeme --
export interface Enceinte {
  id: string;
  nom: string;
  type: string;
  canal_dsp: string;
  hpf_hz?: number | null;
  lpf_hz?: number | null;
}
export interface Paire {
  id: string;
  enceinte_bas: string;
  enceinte_haut: string;
  crossover_hz: number;
  mesure_bas?: number | null;
  mesure_haut?: number | null;
  delay_ms?: number | null;
  inverser_polarite?: boolean | null;
  coherence?: number | null;
  filtres_eq?: any[] | null;
}
export interface Systeme {
  nom: string;
  ip_dsp: string;
  port_dsp: number;
  enceintes: Enceinte[];
  paires: Paire[];
}
export const getSysteme = () => fetchApi<Systeme>("/systeme");
export const saveSysteme = (s: Systeme) =>
  fetchApi<Systeme>("/systeme", { method: "PUT", body: JSON.stringify(s) });
export const addEnceinte = (e: Enceinte) =>
  fetchApi<Enceinte>("/systeme/enceintes", { method: "POST", body: JSON.stringify(e) });
export const deleteEnceinte = (id: string) =>
  fetchApi("/systeme/enceintes/" + id, { method: "DELETE" });
export const addPaire = (p: Paire) =>
  fetchApi<Paire>("/systeme/paires", { method: "POST", body: JSON.stringify(p) });
export const updatePaire = (id: string, p: Paire) =>
  fetchApi<Paire>("/systeme/paires/" + id, { method: "PUT", body: JSON.stringify(p) });
export const deletePaire = (id: string) =>
  fetchApi("/systeme/paires/" + id, { method: "DELETE" });

// -- Presets --
export interface PresetEnceinte {
  id: string;
  nom: string;
  type: string;
  hp: string;
  bande: string;
  hpf_hz?: number | null;
  lpf_hz?: number | null;
  notes: string;
  categorie?: string;
}
export const getPresets = () => fetchApi<{ categories: { nom: string; enceintes: PresetEnceinte[] }[] }>("/presets");
export const getPresetsFlat = () => fetchApi<PresetEnceinte[]>("/presets/flat");
export const addCustomPreset = (p: PresetEnceinte) =>
  fetchApi<PresetEnceinte>("/presets/custom", { method: "POST", body: JSON.stringify(p) });
export const deleteCustomPreset = (id: string) =>
  fetchApi("/presets/custom/" + id, { method: "DELETE" });

// -- Calage --
export const calageDelay = (params: {
  index_mesure_a: number;
  index_mesure_b: number;
  freq_crossover: number;
  canal_delay: string;
  appliquer?: boolean;
}) => fetchApi<any>("/calage/delay", { method: "POST", body: JSON.stringify(params) });

export const calageEQ = (params: {
  index_mesure: number;
  canal_dsp: string;
  seuil_db?: number;
  appliquer?: boolean;
}) => fetchApi<any>("/calage/eq", { method: "POST", body: JSON.stringify(params) });
