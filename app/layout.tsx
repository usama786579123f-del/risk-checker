import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Risk Checker | Sanctions list and SEC filing signals",
  description:
    "Check a company name against the OFAC sanctions list and see recent risk-related SEC filings. Public data only, with a link to every source.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link
          href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  );
}
