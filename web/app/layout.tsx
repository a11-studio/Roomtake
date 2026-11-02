import type { Metadata, Viewport } from "next";
import { Geist } from "next/font/google";
import "./globals.css";

const geistSans = Geist({ variable: "--font-geist-sans", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "Roomtake",
  description: "Film your room. Get a real redesign with products you can buy.",
  icons: { icon: "/RoomTake.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#afc2c9",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <body className={`${geistSans.variable} antialiased`}>
        <main className="mx-auto min-h-dvh w-full max-w-md px-4 pb-16">{children}</main>
      </body>
    </html>
  );
}
