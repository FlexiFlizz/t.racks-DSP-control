"use client";

import { useMemo } from "react";
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from "recharts";

interface FreqData {
  frequences: number[];
  magnitudes: number[];
  phases: number[];
}

interface FreqChartProps {
  dataA: FreqData | null;
  dataB: FreqData | null;
  mode: "magnitude" | "phase";
  labelA?: string;
  labelB?: string;
  crossoverHz?: number;
}

export function FreqChart({
  dataA,
  dataB,
  mode,
  labelA = "Mesure A",
  labelB = "Mesure B",
  crossoverHz,
}: FreqChartProps) {
  const chartData = useMemo(() => {
    if (!dataA && !dataB) return [];
    const source = dataA || dataB;
    if (!source?.frequences) return [];

    // Garder tous les points pour la precision (recharts gere bien jusqu'a ~1000 pts)
    const freqs = source.frequences;
    const maxPts = 500;
    const step = Math.max(1, Math.floor(freqs.length / maxPts));

    const points: any[] = [];
    for (let i = 0; i < freqs.length; i += step) {
      const point: any = { freq: freqs[i] };

      if (dataA?.magnitudes && dataA?.phases) {
        point.a = mode === "magnitude"
          ? Math.round(dataA.magnitudes[i] * 100) / 100
          : Math.round(dataA.phases[i] * 100) / 100;
      }
      if (dataB?.magnitudes && dataB?.phases && i < dataB.frequences.length) {
        point.b = mode === "magnitude"
          ? Math.round(dataB.magnitudes[i] * 100) / 100
          : Math.round(dataB.phases[i] * 100) / 100;
      }

      points.push(point);
    }

    return points;
  }, [dataA, dataB, mode]);

  if (chartData.length === 0) {
    return (
      <div className="h-72 flex items-center justify-center text-muted-foreground text-sm">
        Clique &quot;Charger courbes&quot; pour afficher
      </div>
    );
  }

  const yLabel = mode === "magnitude" ? "dB SPL" : "deg";
  const logTicks = [20, 31.5, 50, 63, 80, 100, 125, 160, 200, 250, 315, 400, 500, 630, 800,
    1000, 1250, 1600, 2000, 2500, 3150, 4000, 5000, 6300, 8000, 10000, 12500, 16000, 20000];
  const visibleTicks = logTicks.filter(
    (f) => f >= (chartData[0]?.freq || 20) * 0.9 && f <= (chartData[chartData.length - 1]?.freq || 20000) * 1.1
  );
  // Afficher seulement certains labels pour pas surcharger
  const labelTicks = [20, 50, 100, 200, 500, 1000, 2000, 5000, 10000, 20000];

  const formatFreq = (f: number) => {
    if (!labelTicks.some((t) => Math.abs(t - f) / t < 0.05)) return "";
    if (f >= 1000) return `${f / 1000}k`;
    return `${f}`;
  };

  // Calculer les bornes Y automatiquement
  const allVals = chartData.flatMap((d) => [d.a, d.b].filter((v) => v !== undefined)) as number[];
  const yMin = Math.floor(Math.min(...allVals) / 5) * 5 - 5;
  const yMax = Math.ceil(Math.max(...allVals) / 5) * 5 + 5;

  return (
    <div className="h-72">
      <ResponsiveContainer width="100%" height="100%">
        <LineChart data={chartData} margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="#222" />
          <XAxis
            dataKey="freq"
            scale="log"
            domain={["dataMin", "dataMax"]}
            ticks={visibleTicks}
            tickFormatter={formatFreq}
            tick={{ fontSize: 9, fill: "#666" }}
            stroke="#333"
            minTickGap={1}
          />
          <YAxis
            domain={[yMin, yMax]}
            tick={{ fontSize: 9, fill: "#666" }}
            stroke="#333"
            width={45}
            tickFormatter={(v) => `${v}`}
            label={{
              value: yLabel,
              angle: -90,
              position: "insideLeft",
              offset: 5,
              style: { fontSize: 9, fill: "#666" },
            }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "#0d1117",
              border: "1px solid #333",
              borderRadius: 6,
              fontSize: 11,
              padding: "6px 10px",
            }}
            labelFormatter={(f) => {
              const freq = Number(f);
              return freq >= 1000 ? `${(freq / 1000).toFixed(2)} kHz` : `${freq.toFixed(1)} Hz`;
            }}
            formatter={(value: number, name: string) => [
              `${value.toFixed(1)} ${yLabel}`,
              name === "a" ? labelA : labelB,
            ]}
          />
          <Legend
            formatter={(value) => (value === "a" ? labelA : labelB)}
            wrapperStyle={{ fontSize: 10, paddingTop: 4 }}
          />
          {crossoverHz && (
            <ReferenceLine
              x={crossoverHz}
              stroke="#f59e0b"
              strokeDasharray="5 5"
              strokeWidth={1}
              label={{
                value: `${crossoverHz} Hz`,
                position: "top",
                style: { fontSize: 9, fill: "#f59e0b" },
              }}
            />
          )}
          {dataA && (
            <Line type="monotone" dataKey="a" stroke="#3b82f6" dot={false} strokeWidth={1.5} />
          )}
          {dataB && (
            <Line type="monotone" dataKey="b" stroke="#f59e0b" dot={false} strokeWidth={1.5} />
          )}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
