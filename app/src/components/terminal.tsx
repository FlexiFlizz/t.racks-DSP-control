"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { Send } from "lucide-react";

const API_BASE = "http://127.0.0.1:8765";
const WS_URL = "ws://127.0.0.1:8765/ws/terminal";

interface TerminalLine {
  text: string;
  type: "input" | "output" | "error" | "system";
}

export function Terminal({
  onCommandStart,
  onCommandEnd,
}: {
  onCommandStart?: () => void;
  onCommandEnd?: () => void;
}) {
  const [lines, setLines] = useState<TerminalLine[]>([
    { text: "Terminal Calage Systeme IA", type: "system" },
    { text: "Tape une commande ou utilise les boutons ci-dessus.", type: "system" },
  ]);
  const [input, setInput] = useState("");
  const [running, setRunning] = useState(false);
  const [history, setHistory] = useState<string[]>([]);
  const [historyIdx, setHistoryIdx] = useState(-1);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  const addLine = useCallback((text: string, type: TerminalLine["type"] = "output") => {
    setLines((l) => [...l, { text, type }]);
  }, []);

  const executeCommand = useCallback(
    async (cmd: string) => {
      if (!cmd.trim()) return;
      setRunning(true);
      onCommandStart?.();
      addLine(`$ ${cmd}`, "input");
      setHistory((h) => [...h, cmd]);
      setHistoryIdx(-1);
      setInput("");

      try {
        // Utiliser WebSocket pour le streaming
        const ws = new WebSocket(WS_URL);
        wsRef.current = ws;

        ws.onopen = () => {
          ws.send(cmd);
        };

        ws.onmessage = (event) => {
          const text = event.data.replace(/\n$/, "");
          if (text) {
            // Split multi-line messages
            text.split("\n").forEach((line: string) => {
              if (line.startsWith("[exit:") || line.startsWith("[erreur:") || line.startsWith("[timeout")) {
                addLine(line, "system");
              } else {
                addLine(line, "output");
              }
            });
          }
        };

        ws.onclose = () => {
          setRunning(false);
          onCommandEnd?.();
          wsRef.current = null;
        };

        ws.onerror = () => {
          // Fallback to HTTP if WebSocket fails
          ws.close();
          fetch(`${API_BASE}/terminal/execute`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ command: cmd }),
          })
            .then((r) => r.json())
            .then((data) => {
              if (data.stdout) {
                data.stdout.split("\n").forEach((line: string) => {
                  if (line) addLine(line, "output");
                });
              }
              if (data.stderr) {
                data.stderr.split("\n").forEach((line: string) => {
                  if (line) addLine(line, "error");
                });
              }
            })
            .catch((e) => addLine(`Erreur: ${e.message}`, "error"))
            .finally(() => {
              setRunning(false);
              onCommandEnd?.();
            });
        };
      } catch {
        setRunning(false);
        onCommandEnd?.();
      }
    },
    [addLine, onCommandStart, onCommandEnd]
  );

  // Expose executeCommand pour les boutons externes
  useEffect(() => {
    (window as any).__terminalExecute = executeCommand;
    return () => {
      delete (window as any).__terminalExecute;
    };
  }, [executeCommand]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !running) {
      executeCommand(input);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      if (history.length > 0) {
        const idx = historyIdx < 0 ? history.length - 1 : Math.max(0, historyIdx - 1);
        setHistoryIdx(idx);
        setInput(history[idx]);
      }
    } else if (e.key === "ArrowDown") {
      e.preventDefault();
      if (historyIdx >= 0) {
        const idx = historyIdx + 1;
        if (idx >= history.length) {
          setHistoryIdx(-1);
          setInput("");
        } else {
          setHistoryIdx(idx);
          setInput(history[idx]);
        }
      }
    }
  };

  const colorClass = (type: TerminalLine["type"]) => {
    switch (type) {
      case "input": return "text-green-400";
      case "error": return "text-red-400";
      case "system": return "text-blue-400";
      default: return "text-foreground";
    }
  };

  return (
    <div className="flex flex-col border border-border rounded-lg overflow-hidden bg-[#0d1117]">
      <div className="flex items-center gap-2 px-3 py-1.5 bg-[#161b22] border-b border-border">
        <div className="flex gap-1.5">
          <div className="w-3 h-3 rounded-full bg-red-500/80" />
          <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
          <div className="w-3 h-3 rounded-full bg-green-500/80" />
        </div>
        <span className="text-xs text-muted-foreground ml-2">Terminal</span>
        {running && (
          <span className="text-xs text-yellow-400 ml-auto animate-pulse">En cours...</span>
        )}
      </div>
      <div
        className="flex-1 p-3 font-mono text-xs leading-5 overflow-auto max-h-80 min-h-40"
        onClick={() => inputRef.current?.focus()}
      >
        {lines.map((line, i) => (
          <div key={i} className={colorClass(line.type)}>
            {line.text}
          </div>
        ))}
        <div ref={bottomRef} />
      </div>
      <div className="flex items-center border-t border-border bg-[#161b22]">
        <span className="text-green-400 text-xs font-mono px-3">$</span>
        <input
          ref={inputRef}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          disabled={running}
          placeholder={running ? "Commande en cours..." : "Taper une commande..."}
          className="flex-1 bg-transparent text-xs font-mono py-2 outline-none text-foreground placeholder:text-muted-foreground"
        />
        <button
          onClick={() => executeCommand(input)}
          disabled={running || !input.trim()}
          className="px-3 py-2 text-muted-foreground hover:text-foreground disabled:opacity-30"
        >
          <Send className="h-3.5 w-3.5" />
        </button>
      </div>
    </div>
  );
}
