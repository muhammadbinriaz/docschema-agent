import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "DocSchema Agent",
  description: "Document → structured fields with human review",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
