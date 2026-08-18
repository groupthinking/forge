import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "FORGE — YouTube → Deployed Software",
  description: "Paste a YouTube URL. Get a live app.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body className="antialiased bg-background text-white min-h-screen">
        {children}
      </body>
    </html>
  );
}
