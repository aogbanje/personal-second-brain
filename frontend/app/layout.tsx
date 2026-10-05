import type { Metadata } from "next";
import "./globals.css";

import { SiteHeader } from "@/components/SiteHeader";

export const metadata: Metadata = {
  title: "PSB",
  description: "Personal second brain",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="min-h-screen">
          <SiteHeader />
          <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
        </div>
      </body>
    </html>
  );
}
