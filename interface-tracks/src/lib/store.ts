"use client";

import { useState, useCallback } from "react";
import type { ChannelState, PEQBand, CrossoverFilter, MatrixRouting, Preset } from "@/types/dsp";
import { DSP206_CONFIG, GEQ_FREQUENCIES } from "@/types/dsp";

function createInitialChannelStates(): Record<string, ChannelState> {
  const states: Record<string, ChannelState> = {};
  for (const ch of [...DSP206_CONFIG.inputs, ...DSP206_CONFIG.outputs]) {
    states[ch.name] = {
      gain: 0, mute: false, level: 0, solo: false,
      phase: false, label: ch.name,
    };
  }
  return states;
}

function createInitialPEQ(): Record<string, PEQBand[]> {
  const peqs: Record<string, PEQBand[]> = {};
  for (const ch of DSP206_CONFIG.inputs) {
    peqs[ch.name] = Array.from({ length: 8 }, (_, i) => ({
      index: i, gain: 0, freq: getDefaultFreq(i, 8), q: 1.41, type: 0, bypass: false,
    }));
  }
  for (const ch of DSP206_CONFIG.outputs) {
    peqs[ch.name] = Array.from({ length: 9 }, (_, i) => ({
      index: i, gain: 0, freq: getDefaultFreq(i, 9), q: 1.41, type: 0, bypass: false,
    }));
  }
  return peqs;
}

function getDefaultFreq(index: number, total: number): number {
  const freqs8 = [63, 125, 250, 500, 1000, 2000, 4000, 8000];
  const freqs9 = [50, 100, 200, 400, 800, 1600, 3150, 6300, 12500];
  return total === 8 ? freqs8[index] : freqs9[index];
}

function createInitialGEQ(): Record<string, number[]> {
  const geqs: Record<string, number[]> = {};
  for (const ch of DSP206_CONFIG.inputs) {
    geqs[ch.name] = Array(GEQ_FREQUENCIES.length).fill(0);
  }
  return geqs;
}

function createInitialMatrix(): MatrixRouting[] {
  return DSP206_CONFIG.outputs.map(ch => ({
    output: ch.name, inputs: ["In A"],
  }));
}

function createInitialCrossover(): Record<string, { hpf: CrossoverFilter; lpf: CrossoverFilter }> {
  const xo: Record<string, { hpf: CrossoverFilter; lpf: CrossoverFilter }> = {};
  for (const ch of DSP206_CONFIG.outputs) {
    xo[ch.name] = {
      hpf: { freq: 20, slope: 3, active: false },
      lpf: { freq: 20000, slope: 3, active: false },
    };
  }
  return xo;
}

function createInitialDelays(): Record<string, number> {
  const delays: Record<string, number> = {};
  for (const ch of DSP206_CONFIG.outputs) {
    delays[ch.name] = 0;
  }
  return delays;
}

function createInitialPresets(): Preset[] {
  return Array.from({ length: 16 }, (_, i) => ({
    index: i,
    name: `Preset ${String(i + 1).padStart(2, "0")}`,
    active: i === 0,
  }));
}

export function useDSPStore() {
  const [connected, setConnected] = useState(false);
  const [channels, setChannels] = useState(createInitialChannelStates);
  const [peqs, setPeqs] = useState(createInitialPEQ);
  const [geqs, setGeqs] = useState(createInitialGEQ);
  const [matrix, setMatrix] = useState(createInitialMatrix);
  const [crossovers, setCrossovers] = useState(createInitialCrossover);
  const [delays, setDelays] = useState(createInitialDelays);
  const [presets, setPresets] = useState(createInitialPresets);

  const setGain = useCallback((channel: string, db: number) => {
    setChannels(prev => ({ ...prev, [channel]: { ...prev[channel], gain: db } }));
  }, []);

  const setMute = useCallback((channel: string, mute: boolean) => {
    setChannels(prev => ({ ...prev, [channel]: { ...prev[channel], mute } }));
  }, []);

  const setSolo = useCallback((channel: string, solo: boolean) => {
    setChannels(prev => ({ ...prev, [channel]: { ...prev[channel], solo } }));
  }, []);

  const setPhase = useCallback((channel: string, phase: boolean) => {
    setChannels(prev => ({ ...prev, [channel]: { ...prev[channel], phase } }));
  }, []);

  const setLabel = useCallback((channel: string, label: string) => {
    setChannels(prev => ({ ...prev, [channel]: { ...prev[channel], label } }));
  }, []);

  const setPEQBand = useCallback((channel: string, bandIndex: number, band: Partial<PEQBand>) => {
    setPeqs(prev => ({
      ...prev,
      [channel]: prev[channel].map((b, i) => i === bandIndex ? { ...b, ...band } : b),
    }));
  }, []);

  const setGEQBand = useCallback((channel: string, bandIndex: number, db: number) => {
    setGeqs(prev => ({
      ...prev,
      [channel]: prev[channel].map((v, i) => i === bandIndex ? db : v),
    }));
  }, []);

  const setMatrixRouting = useCallback((output: string, inputs: string[]) => {
    setMatrix(prev => prev.map(m => m.output === output ? { ...m, inputs } : m));
  }, []);

  const setCrossover = useCallback((channel: string, type: "hpf" | "lpf", filter: Partial<CrossoverFilter>) => {
    setCrossovers(prev => ({
      ...prev,
      [channel]: { ...prev[channel], [type]: { ...prev[channel][type], ...filter } },
    }));
  }, []);

  const setDelay = useCallback((channel: string, ms: number) => {
    setDelays(prev => ({ ...prev, [channel]: ms }));
  }, []);

  const setActivePreset = useCallback((index: number) => {
    setPresets(prev => prev.map(p => ({ ...p, active: p.index === index })));
  }, []);

  return {
    connected, setConnected,
    channels, setGain, setMute, setSolo, setPhase, setLabel,
    peqs, setPEQBand,
    geqs, setGEQBand,
    matrix, setMatrixRouting,
    crossovers, setCrossover,
    delays, setDelay,
    presets, setActivePreset,
  };
}
