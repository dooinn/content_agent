import type { Metadata } from "next";
import {
  Bebas_Neue,
  Cinzel,
  Geist,
  Geist_Mono,
  Inter,
  Montserrat,
  Playfair_Display,
} from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });
const geistMono = Geist_Mono({ variable: "--font-geist-mono", subsets: ["latin"] });

// Caption fonts, loaded for the live caption preview. The renderer bundles the same families.
const montserrat = Montserrat({ variable: "--font-cap-montserrat", subsets: ["latin"], weight: "800" });
const inter = Inter({ variable: "--font-cap-inter", subsets: ["latin"], weight: "700" });
const bebas = Bebas_Neue({ variable: "--font-cap-bebas", subsets: ["latin"], weight: "400" });
const cinzel = Cinzel({ variable: "--font-cap-cinzel", subsets: ["latin"], weight: "700" });
const playfair = Playfair_Display({ variable: "--font-cap-playfair", subsets: ["latin"], weight: "700" });

export const metadata: Metadata = {
  title: "History Shorts Agent",
  description: "Review every stage of an AI-produced 30-second history short.",
};

const fontVariables = [geistSans, geistMono, montserrat, inter, bebas, cinzel, playfair]
  .map((font) => font.variable)
  .join(" ");

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${fontVariables} h-full`}>
      <body className="min-h-full">{children}</body>
    </html>
  );
}
