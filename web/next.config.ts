import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // let a phone on the home Wi-Fi load the dev server's assets
  allowedDevOrigins: ["192.168.*.*", "10.*.*.*"],
};

export default nextConfig;
