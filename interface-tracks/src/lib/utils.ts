import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// Conversion gain : dB <-> valeur brute protocole
export function gainDbToRaw(db: number): number {
  if (db < -20.0) return Math.max(0, Math.round((db + 60) * 2));
  return Math.max(0, Math.round(80 + (db + 20) * 10));
}

export function gainRawToDb(raw: number): number {
  return (raw - 280) / 10.0;
}

// Conversion frequence PEQ
const FREQ_MIN = 19.70;
const FREQ_MAX = 20160.0;
const FREQ_RATIO = FREQ_MAX / FREQ_MIN;

export function freqRawToHz(raw: number): number {
  return FREQ_MIN * Math.pow(FREQ_RATIO, raw / 1000);
}

export function freqHzToRaw(hz: number): number {
  if (hz <= FREQ_MIN) return 0;
  if (hz >= FREQ_MAX) return 1000;
  return Math.round(Math.log(hz / FREQ_MIN) / Math.log(FREQ_RATIO) * 1000);
}

// Conversion Q PEQ
export function qRawToQ(raw: number): number {
  if (raw <= 0) return 0.40;
  if (raw >= 255) return 128.0;
  return 0.40 * Math.pow(320.0, raw / 255.0);
}

export function qToRaw(q: number): number {
  if (q <= 0.40) return 0;
  if (q >= 128.0) return 255;
  return Math.round(Math.log(q / 0.40) / Math.log(320.0) * 255.0);
}

// Gain PEQ/GEQ
export function peqGainDbToRaw(db: number): number {
  return Math.max(0, Math.min(240, Math.round(db * 10 + 120)));
}

export function peqGainRawToDb(raw: number): number {
  return (raw - 120) / 10.0;
}

// Format frequence pour affichage
export function formatFreq(hz: number): string {
  if (hz >= 1000) return `${(hz / 1000).toFixed(hz >= 10000 ? 0 : 1)}k`;
  return `${Math.round(hz)}`;
}

// Format gain pour affichage
export function formatGain(db: number): string {
  if (db === 0) return "0.0";
  return db > 0 ? `+${db.toFixed(1)}` : db.toFixed(1);
}

// Lineaire -> dB pour les metres
export function linearToDb(linear: number): number {
  if (linear <= 0.00001) return -60;
  return Math.max(-60, 20 * Math.log10(linear));
}

// dB -> pourcentage pour l'affichage des metres (0-100%)
export function dbToPercent(db: number): number {
  // -60dB = 0%, 0dB = 100%
  return Math.max(0, Math.min(100, ((db + 60) / 60) * 100));
}
