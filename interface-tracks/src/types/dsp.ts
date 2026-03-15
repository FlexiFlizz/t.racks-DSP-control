// Types pour le DSP t.racks

export interface ProcessorConfig {
  model: string;
  inputs: ChannelInfo[];
  outputs: ChannelInfo[];
}

export interface ChannelInfo {
  id: string;
  index: number;
  name: string;
  type: "input" | "output";
}

export interface ChannelState {
  gain: number;
  mute: boolean;
  level: number;
  solo: boolean;
  phase: boolean;
  label: string;
}

export interface PEQBand {
  index: number;
  gain: number;     // dB (-12 a +12)
  freq: number;     // Hz
  q: number;        // 0.40 a 128
  type: number;     // 0=Peak, 1=LowShelf, 2=HighShelf, etc.
  bypass: boolean;
}

export interface GEQBand {
  index: number;
  gain: number;
}

export interface CrossoverFilter {
  freq: number;
  slope: number;
  active: boolean;
}

export interface MatrixRouting {
  output: string;
  inputs: string[];
}

export interface DelayConfig {
  channel: string;
  delayMs: number;
}

export interface Preset {
  index: number;
  name: string;
  active: boolean;
}

export const DSP206_CONFIG: ProcessorConfig = {
  model: "DSP 206",
  inputs: [
    { id: "0x00", index: 0x00, name: "In A", type: "input" },
    { id: "0x01", index: 0x01, name: "In B", type: "input" },
  ],
  outputs: [
    { id: "0x04", index: 0x04, name: "Out 1", type: "output" },
    { id: "0x05", index: 0x05, name: "Out 2", type: "output" },
    { id: "0x06", index: 0x06, name: "Out 3", type: "output" },
    { id: "0x07", index: 0x07, name: "Out 4", type: "output" },
    { id: "0x08", index: 0x08, name: "Out 5", type: "output" },
    { id: "0x09", index: 0x09, name: "Out 6", type: "output" },
  ],
};

export const PEQ_TYPES = [
  "Peak/Bell", "Low Shelf", "High Shelf",
  "LP 6dB/oct", "LP 12dB/oct", "HP 6dB/oct", "HP 12dB/oct",
  "All Pass 1st", "All Pass 2nd",
] as const;

export const CROSSOVER_SLOPES = [
  "BW 6", "BW 12", "BW 18", "BW 24", "BW 30",
  "BW 36", "BW 42", "BW 48",
  "LR 12", "LR 24", "LR 36", "LR 48",
  "BS 6", "BS 12", "BS 18", "BS 24", "BS 30",
  "BS 36", "BS 42", "BS 48",
] as const;

export const GEQ_FREQUENCIES = [
  20, 25, 31.5, 40, 50, 63, 80, 100, 125, 160,
  200, 250, 315, 400, 500, 630, 800, 1000, 1250, 1600,
  2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000,
] as const;

// Couleurs des bandes PEQ (style Allen & Heath)
export const PEQ_BAND_COLORS = [
  "#ef4444", "#f97316", "#eab308", "#22c55e",
  "#06b6d4", "#3b82f6", "#8b5cf6", "#ec4899", "#f43f5e",
] as const;
