import type { Metadata, Viewport } from "next";
import { Archivo, Instrument_Serif, Syne } from "next/font/google";
import { headers } from "next/headers";
import { Providers } from "@/components/providers";
import { THEME_INIT_SCRIPT } from "@/lib/theme";
import "./globals.css";

// Design system "Noite / Lima / Violeta" (Camarim): Syne é a voz do produto
// (marca, título de página e de modal), Archivo é todo o resto e Instrument
// Serif só aparece na porta (entrada e landing).
const display = Syne({
  weight: ["600", "700", "800"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-display",
});

const body = Archivo({
  subsets: ["latin"],
  display: "swap",
  axes: ["wdth"],
  variable: "--font-body",
});

const serif = Instrument_Serif({
  weight: "400",
  style: ["normal", "italic"],
  subsets: ["latin"],
  display: "swap",
  variable: "--font-serif-face",
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
    <html lang="pt-BR" className={`${display.variable} ${body.variable} ${serif.variable}`} suppressHydrationWarning>
      <head>
        {/* Applies the stored theme before first paint (static string, no user data). */}
        <script nonce={nonce} dangerouslySetInnerHTML={{ __html: THEME_INIT_SCRIPT }} />
      </head>
      <body className="font-sans">
        <a
          href="#conteudo"
          className="fixed left-4 top-4 z-80 -translate-y-24 rounded-control gel-lima px-3 py-3 text-label font-semibold focus:translate-y-0"
        >
          Pular para o conteúdo
        </a>
        <Providers>{children}</Providers>
      </body>
    </html>
  );
}
