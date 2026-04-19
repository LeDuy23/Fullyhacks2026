import type { Metadata } from "next";

import "./globals.css";

export const metadata: Metadata = {
  title: "Fullyhacks 2026",
  description: "Travel planner",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
