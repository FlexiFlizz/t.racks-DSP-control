"use client";

import { cn } from "@/lib/utils";
import { DSP206_CONFIG } from "@/types/dsp";
import type { MatrixRouting } from "@/types/dsp";

interface MatrixSectionProps {
  matrix: MatrixRouting[];
  onRoutingChange: (output: string, inputs: string[]) => void;
}

export function MatrixSection({ matrix, onRoutingChange }: MatrixSectionProps) {
  const inputs = DSP206_CONFIG.inputs;
  const outputs = DSP206_CONFIG.outputs;

  const toggleInput = (output: string, input: string) => {
    const routing = matrix.find(m => m.output === output);
    if (!routing) return;
    const newInputs = routing.inputs.includes(input)
      ? routing.inputs.filter(i => i !== input)
      : [...routing.inputs, input];
    onRoutingChange(output, newInputs);
  };

  return (
    <div className="rounded-lg border border-zinc-800 bg-[#0c0c10] p-4">
      <div className="flex items-center gap-2 mb-4">
        <span className="text-xs font-bold text-zinc-300 uppercase tracking-wider">Matrice de routage</span>
        <span className="text-[9px] text-zinc-600">Entrees vers sorties</span>
      </div>

      <table className="w-auto">
        <thead>
          <tr>
            <th className="w-20" />
            {inputs.map(inp => (
              <th key={inp.name} className="px-3 pb-2 text-center">
                <span className="text-[10px] font-bold text-blue-400">{inp.name}</span>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {outputs.map(out => {
            const routing = matrix.find(m => m.output === out.name);
            return (
              <tr key={out.name} className="group">
                <td className="pr-3 py-1">
                  <span className="text-[10px] font-bold text-amber-400">{out.name}</span>
                </td>
                {inputs.map(inp => {
                  const active = routing?.inputs.includes(inp.name) ?? false;
                  return (
                    <td key={inp.name} className="px-3 py-1 text-center">
                      <button
                        onClick={() => toggleInput(out.name, inp.name)}
                        className={cn(
                          "w-12 h-8 rounded border-2 transition-all text-[10px] font-bold",
                          active
                            ? "bg-blue-500/20 border-blue-500 text-blue-300 shadow-[0_0_10px_rgba(59,130,246,0.25)]"
                            : "bg-zinc-900 border-zinc-800 text-zinc-700 hover:border-zinc-600 hover:text-zinc-500",
                        )}
                      >
                        {active ? "ON" : "\u00B7"}
                      </button>
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
