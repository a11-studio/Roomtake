// Thin client for the FastAPI backend (backend/app/main.py).

// Default: port 8000 on whatever host served the page, so the same dev build
// works on this Mac (localhost) and on a phone on the same Wi-Fi (192.168.x.x).
export const API =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window === "undefined" ? "http://localhost:8000" : `http://${window.location.hostname}:8000`);

export type RoomObject = {
  id: string;
  label: string;
  category: "furniture" | "decor" | "fixture" | "zone";
  best_frame: string;
  mask: string;
  bbox: [number, number, number, number];
  color: { hex: string; name: string };
  confidence: number;
};

export type Room = {
  source_video: string;
  keyframes: { file: string; time_s: number }[];
  objects: RoomObject[];
};

export type Product = {
  id: string;
  name: string;
  category: string;
  price: number;
  currency: string;
  width_cm: number | null;
  image_url: string;
  product_url: string;
  source: string;
};

export type Change = {
  action: "replace" | "add";
  target_id: string;
  target_label: string;
  best_frame: string;
  why: string;
  max_width_cm: number | null;
  fits: boolean;
  product: Product;
};

export type Plan = {
  version: number;
  summary: string;
  style: string;
  changes: Change[];
  total: number;
  currency: string | null;
  within_budget: boolean;
  instruction?: string;
  meta: { model: string; seconds: number };
};

export type Preferences = { style?: string; budget?: number; keep?: string[]; notes?: string };

export type ProgressEvent =
  | { type: "keyframes"; count: number }
  | { type: "uploaded" }
  | { type: "found"; concept: string; count: number }
  | { type: "retry"; concept: string }
  | { type: "done"; objects: number }
  | { type: "status"; status: "done" | "error" | "processing"; error?: string | null };

export const fileUrl = (roomId: string, path: string) => `${API}/api/rooms/${roomId}/files/${path}`;

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export function uploadVideo(file: File, onProgress: (pct: number) => void): Promise<{ id: string }> {
  // XHR rather than fetch: fetch has no upload progress, and room videos are large.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/api/rooms`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => (xhr.status < 300 ? resolve(JSON.parse(xhr.responseText)) : reject(new Error(xhr.responseText)));
    xhr.onerror = () => reject(new Error("Upload failed"));
    const form = new FormData();
    form.append("video", file);
    xhr.send(form);
  });
}

export const getRoom = (id: string) =>
  fetch(`${API}/api/rooms/${id}`).then((r) => json<{ status: string; room?: Room; error?: string }>(r));

export const getPlan = async (id: string): Promise<Plan | null> => {
  const r = await fetch(`${API}/api/rooms/${id}/plan`);
  return r.status === 404 ? null : json<Plan>(r);
};

export const makePlan = (id: string, prefs: Preferences) =>
  fetch(`${API}/api/rooms/${id}/plan`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify(prefs),
  }).then((r) => json<Plan>(r));

export const revisePlan = (id: string, instruction: string) =>
  fetch(`${API}/api/rooms/${id}/plan/revise`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ instruction }),
  }).then((r) => json<Plan>(r));

export const render = (id: string, c: Change) =>
  fetch(`${API}/api/rooms/${id}/render`, {
    method: "POST",
    headers: { "content-type": "application/json" },
    body: JSON.stringify({ object_id: c.target_id, product_id: c.product.id, action: c.action }),
  }).then((r) => json<{ before: string; after: string }>(r));
