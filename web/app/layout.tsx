import type { Metadata, Viewport } from "next";
import "./globals.css";

// Google Sans Flex is newer than next/font's font list, so it comes straight
// from Google Fonts (variable: optical size 6-144, weight 300-800).
const FONT_CSS =
  "https://fonts.googleapis.com/css2?family=Google+Sans+Flex:opsz,wght@6..144,300..800&display=swap";

export const metadata: Metadata = {
  title: "Roomtake",
  description: "Film your room. Get a real redesign with products you can buy.",
  icons: { icon: "/RoomTake.svg" },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  themeColor: "#ffffff",
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="" />
        <link rel="stylesheet" href={FONT_CSS} />
      </head>
      <body className="antialiased">
        <main className="mx-auto min-h-dvh w-full max-w-md px-5 pb-20 md:max-w-3xl md:px-8 lg:max-w-6xl lg:px-10">{children}</main>
      </body>
    </html>
  );
}
