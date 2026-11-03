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
  approx_size: { frame_area_pct: number; bbox_w_pct: number; bbox_h_pct: number };
};

export type Room = {
  source?: "photos";
  source_video: string | null;
  keyframes: { file: string; time_s: number }[];
  views: { file: string; frame: number; kind: "main" | "zone"; label: string }[];
  objects: RoomObject[];
};

export type Product = {
  id: string;
  name: string;
  name_en?: string | null;
  category: string;
  style?: string | null;
  color?: string | null;
  material?: string | null;
  price: number;
  currency: string;
  price_eur: number;
  width_cm: number | null;
  depth_cm?: number | null;
  height_cm?: number | null;
  image_url: string;
  product_url: string;
  source: string;
};

export type Preferences = { style?: string; budget?: number; keep?: string[]; notes?: string };

export type ProgressEvent =
  | { type: "keyframes"; count: number }
  | { type: "uploaded" }
  | { type: "found"; concept: string; count: number }
  | { type: "retry"; concept: string }
  | { type: "done"; objects: number }
  | { type: "status"; status: "done" | "error" | "processing"; error?: string | null };

/** Smaller product photo for thumbnails (Shopify CDN resizes on the fly). */
export const thumb = (url: string, width = 300) =>
  url.includes("cdn.shopify.com") ? `${url}${url.includes("?") ? "&" : "?"}width=${width}` : url;

export const fileUrl = (roomId: string, path: string) => `${API}/api/rooms/${roomId}/files/${path}`;

async function json<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

/** 1-3 photos of the room (the first is the room itself, e.g. a balcony can follow). */
export function uploadPhotos(files: File[], onProgress: (pct: number) => void): Promise<{ id: string }> {
  // XHR rather than fetch: fetch has no upload progress, and phone photos are several MB.
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API}/api/rooms`);
    xhr.upload.onprogress = (e) => e.lengthComputable && onProgress(Math.round((e.loaded / e.total) * 100));
    xhr.onload = () => {
      if (xhr.status < 300) return resolve(JSON.parse(xhr.responseText));
      let detail = `Upload failed (${xhr.status})`;
      try {
        detail = JSON.parse(xhr.responseText).detail ?? detail;
      } catch {}
      reject(new Error(detail));
    };
    xhr.onerror = () => reject(new Error("Upload failed"));
    const form = new FormData();
    files.slice(0, 3).forEach((f) => form.append("photos", f));
    xhr.send(form);
  });
}

export const getRoom = (id: string) =>
  fetch(`${API}/api/rooms/${id}`).then((r) => json<{ status: string; room?: Room; error?: string }>(r));

export type ProductUse = {
  product: Product;
  for: string; // the piece it becomes ("sofa") or "add"
  view: string; // "main" or a zone label ("balcony floor")
  note: string;
};

export type LookView = {
  file: string;
  kind: "main" | "zone";
  label: string;
  after: string | null;
  current: string | null;
};

export type Look = {
  id: string;
  parent: string | null;
  instruction: string | null;
  prefs?: Preferences;
  status: "brief" | "rendering" | "checking" | "done" | "error";
  error: string | null;
  brief: null | {
    title: string;
    summary: string;
    why?: string;
    palette?: string[];
    materials?: string[];
  };
  views: LookView[];
  products: ProductUse[];
  layout_iou: { mean: number | null } | null;
  shop: { count: number; total: number; currency: string | null };
};

const post = <T,>(url: string, body: unknown) =>
  fetch(url, { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) }).then((r) =>
    json<T>(r),
  );

export const listLooks = (id: string) =>
  fetch(`${API}/api/rooms/${id}/looks`).then((r) => json<{ id: string; status: string }[]>(r));
export const getLook = (id: string, lookId: string) =>
  fetch(`${API}/api/rooms/${id}/looks/${lookId}`).then((r) => json<Look>(r));
export const createLook = (id: string, prefs: Preferences) => post<Look>(`${API}/api/rooms/${id}/looks`, prefs);
export const reviseLook = (id: string, lookId: string, instruction: string) =>
  post<Look>(`${API}/api/rooms/${id}/looks/${lookId}/revise`, { instruction });

export type Catalog = {
  categories: string[];
  styles: string[];
  counts: Record<string, number>;
  products: Product[];
  source: string | null;
  editable: boolean;
};

export const getCatalog = () => fetch(`${API}/api/catalog`).then((r) => json<Catalog>(r));
export const importProduct = (url: string) => post<{ variants: Product[] }>(`${API}/api/catalog/import`, { url });
export const saveProduct = (p: Product) => post<Product>(`${API}/api/catalog/products`, p);
export const removeProduct = (id: string) =>
  fetch(`${API}/api/catalog/products/${encodeURIComponent(id)}`, { method: "DELETE" }).then((r) => json<unknown>(r));

/** Speech to text for the stylist input (Muse Voice Transcribe on the server). */
export async function transcribe(audio: Blob): Promise<string> {
  const form = new FormData();
  form.append("audio", audio, audio.type.includes("mp4") ? "speech.mp4" : "speech.webm");
  const { text } = await json<{ text: string }>(await fetch(`${API}/api/transcribe`, { method: "POST", body: form }));
  return text;
}
