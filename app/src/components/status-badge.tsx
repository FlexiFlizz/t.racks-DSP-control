"use client";

import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

export function StatusBadge({
  connected,
  label,
}: {
  connected: boolean;
  label: string;
}) {
  return (
    <Badge
      variant="outline"
      className={cn(
        "gap-1.5",
        connected ? "border-green-500/50 text-green-400" : "border-red-500/50 text-red-400"
      )}
    >
      <span
        className={cn(
          "h-2 w-2 rounded-full",
          connected ? "bg-green-500" : "bg-red-500"
        )}
      />
      {label}
    </Badge>
  );
}
