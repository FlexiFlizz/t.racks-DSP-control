"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Activity,
  SlidersHorizontal,
  Target,
  Settings,
  Waves,
  Speaker,
} from "lucide-react";
import { cn } from "@/lib/utils";

const nav = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/mesures", label: "Mesures", icon: Activity },
  { href: "/enceintes", label: "Enceintes", icon: Speaker },
  { href: "/dsp", label: "DSP", icon: SlidersHorizontal },
  { href: "/calage", label: "Calage", icon: Target },
  { href: "/parametres", label: "Parametres", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-56 border-r border-border bg-card flex flex-col">
      <div className="p-4 border-b border-border">
        <div className="flex items-center gap-2">
          <Waves className="h-6 w-6 text-primary" />
          <div>
            <h1 className="text-sm font-bold leading-none">Calage Systeme</h1>
            <span className="text-[10px] text-muted-foreground">v0.1.0</span>
          </div>
        </div>
      </div>
      <nav className="flex-1 p-2 space-y-1">
        {nav.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className={cn(
              "flex items-center gap-3 px-3 py-2 rounded-md text-sm transition-colors",
              pathname === href
                ? "bg-accent text-accent-foreground font-medium"
                : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
            )}
          >
            <Icon className="h-4 w-4" />
            {label}
          </Link>
        ))}
      </nav>
    </aside>
  );
}
