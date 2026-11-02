# Roomtake web

Mobile-first Next.js app over the FastAPI backend (`../backend`).

```bash
npm install
npm run dev            # http://localhost:3000, expects the API on :8000
```

Set `NEXT_PUBLIC_API_URL` to point at another backend.

- `app/page.tsx` — film/upload a room, or open the demo room
- `app/room/[id]/page.tsx` — analysis → preferences → plan
- `components/Analysis.tsx` — live "found" chips from the SAM progress stream
- `components/Preferences.tsx` — style, budget, items to keep
- `components/PlanView.tsx` — changes with before/after, shopping list, revise bar
- `app/globals.css` — design tokens (brand `#AFC2C9`)
