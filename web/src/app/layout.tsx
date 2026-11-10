import type { Metadata, Viewport } from "next";
import ThemeControls from "@/components/ThemeControls";
import "./globals.css";

export const metadata: Metadata = {
  title: "IA no aprendizado de programação",
  description: "Pesquisa acadêmica anônima sobre o uso de assistentes de IA por estudantes de computação.",
  robots: { index: false, follow: false },
};

export const viewport: Viewport = { width: "device-width", initialScale: 1 };

// Aplica tema e contraste antes da primeira pintura (evita "piscar").
const initTheme = `(function(){try{var r=document.documentElement,g=function(k){try{return localStorage.getItem(k)}catch(e){return null}};
var t=g("tema");if(t!=="light"&&t!=="dark"){t=matchMedia("(prefers-color-scheme: dark)").matches?"dark":"light"}
r.dataset.theme=t;var c=g("contraste");if(c==="high"||(c===null&&matchMedia("(prefers-contrast: more)").matches)){r.dataset.contrast="high"}}catch(e){}})();`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="pt-BR" suppressHydrationWarning>
      <head>
        <script dangerouslySetInnerHTML={{ __html: initTheme }} />
      </head>
      <body className="flex min-h-dvh flex-col antialiased">
        <ThemeControls />
        {children}
      </body>
    </html>
  );
}
