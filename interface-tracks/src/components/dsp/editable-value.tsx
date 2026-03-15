"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";

interface EditableValueProps {
  value: number;
  onChange: (value: number) => void;
  min: number;
  max: number;
  step?: number;
  precision?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
  formatFn?: (v: number) => string;
}

export function EditableValue({
  value, onChange, min, max,
  step = 0.1, precision = 1,
  suffix = "", prefix = "",
  className, formatFn,
}: EditableValueProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  const displayValue = formatFn
    ? formatFn(value)
    : `${prefix}${value > 0 ? "+" : ""}${value.toFixed(precision)}${suffix}`;

  const startEdit = useCallback(() => {
    setEditing(true);
    setEditValue(value.toFixed(precision));
  }, [value, precision]);

  const commitEdit = useCallback(() => {
    setEditing(false);
    const parsed = parseFloat(editValue);
    if (!isNaN(parsed)) {
      onChange(Math.max(min, Math.min(max, parsed)));
    }
  }, [editValue, onChange, min, max]);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  // Scroll wheel to adjust value
  const handleWheel = useCallback((e: React.WheelEvent) => {
    e.preventDefault();
    const delta = e.deltaY > 0 ? -step : step;
    const fine = e.shiftKey ? delta / 10 : e.ctrlKey ? delta * 10 : delta;
    onChange(Math.max(min, Math.min(max, +(value + fine).toFixed(precision))));
  }, [value, onChange, min, max, step, precision]);

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={commitEdit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commitEdit();
          if (e.key === "Escape") setEditing(false);
        }}
        className={cn(
          "bg-background border border-primary rounded px-1 py-0 text-center font-mono text-xs w-16 outline-none",
          className,
        )}
      />
    );
  }

  return (
    <span
      onDoubleClick={startEdit}
      onWheel={handleWheel}
      title="Double-clic pour editer, molette pour ajuster (Shift=fin, Ctrl=gros)"
      className={cn(
        "font-mono text-xs tabular-nums cursor-default select-none hover:text-primary transition-colors",
        className,
      )}
    >
      {displayValue}
    </span>
  );
}

// Editable text label (for channel names)
interface EditableLabelProps {
  value: string;
  onChange: (value: string) => void;
  className?: string;
  maxLength?: number;
}

export function EditableLabel({ value, onChange, className, maxLength = 8 }: EditableLabelProps) {
  const [editing, setEditing] = useState(false);
  const [editValue, setEditValue] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (editing && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [editing]);

  const commit = () => {
    setEditing(false);
    if (editValue.trim()) onChange(editValue.trim());
  };

  if (editing) {
    return (
      <input
        ref={inputRef}
        type="text"
        value={editValue}
        maxLength={maxLength}
        onChange={(e) => setEditValue(e.target.value)}
        onBlur={commit}
        onKeyDown={(e) => {
          if (e.key === "Enter") commit();
          if (e.key === "Escape") setEditing(false);
        }}
        className={cn(
          "bg-background border border-primary rounded px-1 py-0 text-center text-xs w-16 outline-none",
          className,
        )}
      />
    );
  }

  return (
    <span
      onDoubleClick={() => { setEditing(true); setEditValue(value); }}
      title="Double-clic pour renommer"
      className={cn(
        "text-xs font-medium cursor-default select-none hover:text-primary transition-colors truncate",
        className,
      )}
    >
      {value}
    </span>
  );
}
