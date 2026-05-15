import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "CMPE 272 — CIAA Transfer Demo",
  description: "Frontend for testing Approach A (mTLS) and Approach B (envelope/broker)",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>
        <div className="container">{children}</div>
      </body>
    </html>
  );
}
