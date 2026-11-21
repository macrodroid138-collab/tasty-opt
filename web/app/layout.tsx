import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Sigma desk",
  description: "Watch Sigma Carry and Sigma Clip decide, one print at a time.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
