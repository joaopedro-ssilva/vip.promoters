import type { Metadata, Viewport } from "next";
import { Barlow_Condensed, Manrope } from "next/font/google";
import { headers } from "next/headers";
import { Providers } from "@/components/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

const display = Barlow_Condensed({
  weight: ["600", "700"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
});

const body = Manrope({
  subsets: ["latin"],
  display: "swap",
  variable: "--font-body",
});

export const metadata: Metadata = {
  title: { default: "VIP Promoters", template: "%s · VIP Promoters" },
  description:
    "Organize campanhas no Instagram, acompanhe participações e recompense seus promoters.",
  robots: { index: true, follow: true },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  colorScheme: "dark light",
};

export default async function RootLayout({ children }: { children: React.ReactNode }) {
  // Reading the request headers opts every page into per-request rendering,
  // which is what lets Next.js stamp the CSP nonce (set in src/proxy.ts) on its scripts.
  const nonce = (await headers()).get("x-nonce") ?? undefined;

  return (
    <html lang="pt-BR" className={`${display.variable} ${body.variable}`} suppressHydrationWarning>
      <head>
        {/* Applies the stored theme before first paint (static string, no user data). */}
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans">
        <a
          href="#conteudo"
          className="fixed left-4 top-4 z-80 -translate-y-24 rounded-control border border-accent bg-surface px-3 py-3 text-label text-ink focus:translate-y-0"
        >
          Pular para o conteúdo
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
