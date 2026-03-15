import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "t.racks DSP Controller",
  description: "Interface de controle pour processeurs t.racks DSP",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="fr" className="dark">
      <body className="min-h-screen antialiased">
        {children}
      </body>
    </html>
  );
}
