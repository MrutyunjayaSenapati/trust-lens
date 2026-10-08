import type { Metadata, Viewport } from "next";
import "@fontsource-variable/fraunces/index.css";
import "@fontsource/hind/400.css";
import "@fontsource/hind/500.css";
import "@fontsource/hind/600.css";
import "@fontsource/tiro-devanagari-hindi/400.css";
import "@fontsource/dm-mono/400.css";
import "@fontsource/dm-mono/500.css";
import "./globals.css";
import { LangProvider } from "@/lib/i18n";
import PwaClient from "@/components/PwaClient";

export const metadata: Metadata = {
  title: "TrustLens — is this real?",
  description: "Paste a suspicious job offer, seller message, deal or link. TrustLens cross-checks it against live Google data via SerpApi and shows its evidence.",
  manifest: "/manifest.webmanifest",
  applicationName: "TrustLens",
  appleWebApp: { capable: true, title: "TrustLens", statusBarStyle: "default" },
  icons: { icon: "/icons/192", apple: "/icons/180" },
};

export const viewport: Viewport = { themeColor: "#1A1633", width: "device-width", initialScale: 1 };

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen font-sans antialiased">
        {/* ink-bleed filter used by the verdict stamp */}
        <svg aria-hidden width="0" height="0" style={{ position: "absolute" }}>
          <filter id="rough" x="-5%" y="-5%" width="110%" height="110%">
            <feTurbulence type="fractalNoise" baseFrequency="0.85" numOctaves="2" seed="4" result="n" />
            <feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" />
          </filter>
        </svg>
        <LangProvider>
          <PwaClient />
          {children}
        </LangProvider>
      </body>
    </html>
  );
}
