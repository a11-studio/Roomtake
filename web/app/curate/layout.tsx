import { notFound } from "next/navigation";

// The catalog editor is for us, on `npm run dev`; deployed builds answer 404.
export default function CurateLayout({ children }: { children: React.ReactNode }) {
  if (process.env.NODE_ENV !== "development") notFound();
  return children;
}
