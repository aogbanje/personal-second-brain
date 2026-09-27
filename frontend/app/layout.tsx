import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "PSB",
  description: "Personal second brain",
};

const NAV = [
  { href: "/dashboard", label: "Library" },
  { href: "/chat", label: "Chat" },
  { href: "/graph", label: "Graph" },
];

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <header className="border-b border-neutral-800 bg-neutral-900/50 backdrop-blur sticky top-0 z-20">
            <nav className="mx-auto flex max-w-6xl items-center gap-6 px-6 py-3">
              <Link href="/dashboard" className="font-semibold tracking-tight">
                PSB
              </Link>
              <div className="flex gap-1 text-sm">
                {NAV.map((item) => (
                  <Link
                    key={item.href}
                    href={item.href}
                    className="rounded-md px-3 py-1.5 text-neutral-400 transition hover:bg-neutral-800 hover:text-neutral-100"
                  >
                    {item.label}
                  </Link>
                ))}
              </div>
            </nav>
          </header>
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
