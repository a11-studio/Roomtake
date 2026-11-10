"use client";

import { useEffect } from "react";
import { API } from "@/lib/api";

// The API machine stops itself when nobody uses it and takes a few seconds to
// start again. Knock as soon as any page opens, so it is awake by the time
// someone taps "Try our demo" or uploads a photo.
export function WakeApi() {
  useEffect(() => {
    fetch(`${API}/api/health`, { cache: "no-store" }).catch(() => {});
  }, []);
  return null;
}
