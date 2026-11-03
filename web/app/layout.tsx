import type { Metadata, Viewport } from "next";
import "./globals.css";

// Google Sans Flex is newer than next/font's font list, so it comes straight
// from Google Fonts (variable: optical size 6-144, weight 300-800).
const FONT_CSS =
  "https://fonts.googleapis.com/css2?family=Google+Sans+Flex:opsz,wght@6..144,300..800&display=swap";

const TITLE = "RoomTake: Same room. Better take.";
const DESCRIPTION = "Snap your room. Get a real redesign with products you can buy.";

export const metadata: Metadata = {
  // absolute URLs for the share card (og:image) need the site's address
  metadataBase: new URL(process.env.NEXT_PUBLIC_SITE_URL ?? "https://roomtake-meta.vercel.app"),
  title: TITLE,
  description: DESCRIPTION,
  icons: { icon: "/favicon.png", apple: "/favicon.png" },
  openGraph: {
    type: "website",
    siteName: "RoomTake",
    title: TITLE,
    description: DESCRIPTION,
    url: "/",
    images: [{ url: "/og-image.png", width: 1200, height: 630, alt: "RoomTake" }],
  },
  twitter: {
    card: "summary_large_image",
    title: TITLE,
    description: DESCRIPTION,
    images: ["/og-image.png"],
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  // no theme-color: browsers tint their bars from each page's own background
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
