"use client";

import { useRef } from "react";

// The RoomTake logo as inline SVG. A tap spins the chair once around its own
// vertical axis, in 3D: while it turns, the flat logo chair hands over to a
// small 3D model of the same chair (seat, four splayed legs, the rear two
// running up into a curved backrest band), projected with perspective every
// frame and drawn flat in the logo's one colour, so it stays a silhouette.
// At rest the model is posed to sit on the logo (fitted to it, ~1 unit off),
// so the hand-over is a quick cross-fade, not a jump.
//
// The motion: a small crouch and wind-up the other way, a lift as it starts
// to turn, a turn that is still fast as it comes round and is caught at the
// front with a short swing, and a soft landing that squashes it for a moment.

const CHAIR = "M37.4236 0.0410156C43.9517 -0.251889 49.1723 1.00142 54.4773 4.88086C55.2048 4.90311 56.4402 5.37228 56.4949 6.21094C56.5589 7.20336 56.2824 8.40528 56.1091 9.39941C55.8212 11.0528 55.5135 12.7027 55.1853 14.3486C55.1293 14.6337 54.8819 15.7701 54.8982 16.0098C55.4307 16.2122 57.4079 16.2301 58.1482 16.3291C59.4002 16.4966 60.9172 16.524 62.1912 16.6777C62.6419 16.7322 63.5931 16.7161 63.9607 16.8867C64.0825 17.229 63.9715 17.4707 63.7468 17.7129C63.7827 18.766 63.9039 20.0103 63.9773 21.0762L64.4431 27.8008C64.7624 32.3984 65.018 37.1965 65.4089 41.7754C64.9361 42.2571 64.1757 42.4169 63.5886 42.0039C63.4991 41.9408 63.3059 41.7289 63.2917 41.6191C63.2228 41.0676 63.1802 40.5078 63.1345 39.9531C63.0445 38.8495 62.9469 37.7459 62.8425 36.6436L61.9099 26.1328C61.7568 24.3953 61.6303 22.446 61.4216 20.7236C60.6913 20.8629 59.7015 20.9716 58.946 21.0752L53.8074 21.7793C53.647 22.8136 53.407 23.9609 53.2126 24.9961L52.2322 30.2783L51.4187 34.6318C51.3466 35.021 51.019 37.1873 50.7908 37.4268C50.3535 37.8821 48.8859 37.8935 49.0417 36.7764C49.1093 36.2924 49.2624 35.6204 49.3396 35.0957L49.95 30.9521L50.7576 25.6064C50.922 24.5053 51.0771 23.3113 51.282 22.2227C50.2759 22.3159 48.9551 22.5531 47.9138 22.6953C47.2062 22.8307 46.484 22.8846 45.7751 23.0107C45.843 23.9829 45.8334 25.2633 45.8425 26.2549L45.9089 30.4121L46.1765 46.3623C45.8928 46.7799 45.494 46.9051 45.0027 46.9414C44.6978 46.9642 44.345 46.8764 44.1238 46.6602C43.9947 46.534 43.9221 46.4101 43.9138 46.2246C43.8665 45.3556 43.8481 44.4623 43.8201 43.5938L43.6511 38.4629L43.1394 22.9473C42.4766 22.8819 41.628 22.7379 40.9617 22.6426L37.0701 22.0859C35.8915 21.9149 34.7032 21.5738 33.5554 21.9453C33.4592 22.6228 33.2119 23.6874 33.071 24.3848L32.0447 29.3965L29.4802 41.8926C28.8298 42.5387 27.918 42.5029 27.45 41.6455C27.7036 40.4353 27.9178 38.9951 28.1306 37.7666L29.5173 29.6533C30.62 23.228 31.8207 16.7004 32.8484 10.2705C32.3972 10.1849 32.0681 10.1712 31.616 10.1709C31.4805 10.0839 31.3945 9.99953 31.2761 9.89258L30.2332 5.2373C30.0445 4.40244 29.8333 3.53743 29.6794 2.69434C29.6572 2.57228 29.7051 2.37053 29.7341 2.24512C30.4099 1.48668 31.0101 1.14101 31.9978 0.885742C33.7913 0.42226 35.5809 0.172244 37.4236 0.0410156ZM53.5037 8.55762C51.6039 8.5124 49.2552 8.39573 47.3816 8.5C44.0086 8.61296 40.6146 8.87333 37.2468 9.10938C36.8395 9.13793 36.4252 9.1639 36.0193 9.20508L36.0144 9.26172C35.9571 9.84306 35.7165 10.9164 35.6003 11.5166L34.7566 15.9111C34.6218 16.6175 34.4096 17.5623 34.3259 18.2461C34.8536 18.5436 39.4303 18.3694 40.1306 18.1748C43.1686 17.9057 46.208 17.3168 49.1628 16.585C50.1947 16.3294 51.3065 16.1259 52.3562 15.9424L53.5037 8.55762Z";

const WORDS = [
  "M87.3569 71.3297C85.8302 71.3297 84.5835 70.8197 83.6169 69.7997C82.6502 68.773 82.1669 67.463 82.1669 65.8697C82.1669 64.3097 82.6435 63.0164 83.5969 61.9897C84.5569 60.9564 85.7769 60.4397 87.2569 60.4397C88.7302 60.4397 89.9235 60.893 90.8369 61.7997C91.7569 62.6997 92.2169 63.8297 92.2169 65.1897V66.2997H83.3269V64.8397H90.0769C90.0302 64.0997 89.7535 63.4864 89.2469 62.9997C88.7469 62.513 88.0835 62.2697 87.2569 62.2697C86.3702 62.2697 85.6502 62.593 85.0969 63.2397C84.5502 63.8797 84.2769 64.7464 84.2769 65.8397C84.2769 66.9664 84.5835 67.863 85.1969 68.5297C85.8169 69.1897 86.5969 69.5197 87.5369 69.5197C87.9769 69.5197 88.3569 69.4597 88.6769 69.3397C88.9969 69.2197 89.2835 69.0564 89.5369 68.8497C89.7969 68.6364 90.0902 68.293 90.4169 67.8197L91.9869 68.7497C91.5869 69.4497 91.1669 69.9697 90.7269 70.3097C90.2869 70.643 89.8002 70.8964 89.2669 71.0697C88.7402 71.243 88.1035 71.3297 87.3569 71.3297Z",
  "M73.5248 69.0197V66.3797L78.9748 60.7697H81.7648L73.5248 69.0197ZM72.4048 70.9997V56.6797H74.5748V70.9997H72.4048ZM79.2348 70.9997L75.7848 65.6697L77.3048 64.1697L81.9148 70.9997H79.2348Z",
  "M64.5496 71.3297C63.423 71.3297 62.5096 71.013 61.8096 70.3797C61.1096 69.7464 60.7596 68.9264 60.7596 67.9197C60.7596 66.8864 61.163 66.063 61.9696 65.4497C62.7763 64.8297 63.8163 64.5197 65.0896 64.5197C65.6363 64.5197 66.1663 64.5797 66.6796 64.6997C67.193 64.813 67.6096 64.9597 67.9296 65.1397V64.5197C67.9296 63.8264 67.6863 63.2697 67.1996 62.8497C66.713 62.423 66.0796 62.2097 65.2996 62.2097C64.8663 62.2097 64.4996 62.2597 64.1996 62.3597C63.8996 62.453 63.6363 62.5764 63.4096 62.7297C63.183 62.8764 62.973 63.0497 62.7796 63.2497C62.5863 63.4497 62.4896 63.5497 62.4896 63.5497L61.1096 62.3597C61.1096 62.3597 61.2563 62.2197 61.5496 61.9397C61.843 61.6597 62.1663 61.4064 62.5196 61.1797C62.8796 60.953 63.2863 60.773 63.7396 60.6397C64.1996 60.5064 64.7563 60.4397 65.4096 60.4397C66.8496 60.4397 67.9763 60.803 68.7896 61.5297C69.603 62.2564 70.0096 63.2597 70.0096 64.5397V70.9997H67.9296V68.6297L68.5596 69.5997H67.8696C67.5563 70.1064 67.103 70.523 66.5096 70.8497C65.9163 71.1697 65.263 71.3297 64.5496 71.3297ZM64.9796 69.6497C65.8063 69.6497 66.503 69.3564 67.0696 68.7697C67.643 68.183 67.9296 67.453 67.9296 66.5797V66.5697C67.623 66.3764 67.253 66.223 66.8196 66.1097C66.393 65.9964 65.9463 65.9397 65.4796 65.9397C64.6863 65.9397 64.053 66.0997 63.5796 66.4197C63.1063 66.7397 62.8696 67.2197 62.8696 67.8597C62.8696 68.3997 63.0663 68.833 63.4596 69.1597C63.853 69.4864 64.3596 69.6497 64.9796 69.6497Z",
  "M55.3123 70.9997V57.7297H57.4923V70.9997H55.3123ZM51.3323 58.7397V56.6797H61.4523V58.7397H51.3323Z",
  "M35.686 70.9997V60.7697H37.766V62.5197L37.556 62.2697H37.826C38.1194 61.7364 38.5627 61.2997 39.156 60.9597C39.756 60.613 40.3894 60.4397 41.056 60.4397C41.7827 60.4397 42.4227 60.613 42.976 60.9597C43.536 61.3064 43.9427 61.783 44.196 62.3897C44.5827 61.7497 45.0794 61.2664 45.686 60.9397C46.2927 60.6064 46.966 60.4397 47.706 60.4397C48.8794 60.4397 49.7727 60.7897 50.386 61.4897C50.9994 62.1897 51.306 63.173 51.306 64.4397V70.9997H49.156V64.8097C49.156 63.963 48.9827 63.3364 48.636 62.9297C48.2894 62.523 47.7594 62.3197 47.046 62.3197C46.346 62.3197 45.7594 62.603 45.286 63.1697C44.8194 63.7364 44.586 64.4297 44.586 65.2497V70.9997H42.416V64.8197C42.416 63.9797 42.2427 63.353 41.896 62.9397C41.5494 62.5264 41.0227 62.3197 40.316 62.3197C39.6227 62.3197 39.0394 62.6097 38.566 63.1897C38.0927 63.763 37.856 64.4597 37.856 65.2797V70.9997H35.686Z",
  "M28.4158 71.3297C26.8624 71.3297 25.5791 70.813 24.5658 69.7797C23.5524 68.7397 23.0458 67.4397 23.0458 65.8797C23.0458 64.293 23.5524 62.9897 24.5658 61.9697C25.5858 60.9497 26.8691 60.4397 28.4158 60.4397C29.9624 60.4397 31.2458 60.953 32.2658 61.9797C33.2858 63.0064 33.7958 64.3064 33.7958 65.8797C33.7958 67.4397 33.2891 68.7397 32.2758 69.7797C31.2624 70.813 29.9758 71.3297 28.4158 71.3297ZM28.4158 69.4297C29.3291 69.4297 30.0958 69.0997 30.7158 68.4397C31.3358 67.773 31.6458 66.9197 31.6458 65.8797C31.6458 64.8197 31.3324 63.9664 30.7058 63.3197C30.0858 62.6664 29.3224 62.3397 28.4158 62.3397C27.5024 62.3397 26.7324 62.6664 26.1058 63.3197C25.4858 63.973 25.1758 64.8264 25.1758 65.8797C25.1758 66.9197 25.4824 67.773 26.0958 68.4397C26.7158 69.0997 27.4891 69.4297 28.4158 69.4297Z",
  "M16.3455 71.3297C14.7921 71.3297 13.5088 70.813 12.4955 69.7797C11.4821 68.7397 10.9755 67.4397 10.9755 65.8797C10.9755 64.293 11.4821 62.9897 12.4955 61.9697C13.5155 60.9497 14.7988 60.4397 16.3455 60.4397C17.8921 60.4397 19.1755 60.953 20.1955 61.9797C21.2155 63.0064 21.7255 64.3064 21.7255 65.8797C21.7255 67.4397 21.2188 68.7397 20.2055 69.7797C19.1921 70.813 17.9055 71.3297 16.3455 71.3297ZM16.3455 69.4297C17.2588 69.4297 18.0255 69.0997 18.6455 68.4397C19.2655 67.773 19.5755 66.9197 19.5755 65.8797C19.5755 64.8197 19.2621 63.9664 18.6355 63.3197C18.0155 62.6664 17.2521 62.3397 16.3455 62.3397C15.4321 62.3397 14.6621 62.6664 14.0355 63.3197C13.4155 63.973 13.1055 64.8264 13.1055 65.8797C13.1055 66.9197 13.4121 67.773 14.0255 68.4397C14.6455 69.0997 15.4188 69.4297 16.3455 69.4297Z",
  "M0 70.9997V56.6797H5.11C6.39 56.6797 7.48 57.0864 8.38 57.8997C9.28667 58.713 9.74 59.763 9.74 61.0497C9.74 62.3364 9.29333 63.393 8.4 64.2197C7.51333 65.0397 6.33667 65.4497 4.87 65.4497H1.04V63.6297H4.95C5.66333 63.6297 6.27333 63.393 6.78 62.9197C7.28667 62.4464 7.54 61.8397 7.54 61.0997C7.54 60.4264 7.29667 59.8564 6.81 59.3897C6.32333 58.923 5.73667 58.6897 5.05 58.6897H2.19V70.9997H0ZM7.89 70.9997L3.62 64.4897L5.97 64.3797L10.5 70.9997H7.89Z",
];

// ---- the 3D chair, in logo units (y up, z toward you) ----
const W = 8.37, D = 6.37, H = 16.54, THICK = 1.5; // seat half width, half depth, height, thickness
const FRONT_SPLAY = [-0.1, 0.71], REAR_SPLAY = [1.48, 4.49]; // feet past the seat corners (x, z)
const BAND_LO = 22.2, BAND_HI = 26; // backrest band
// camera, fitted to the logo
const YAW = 0.624, PITCH = 0.26, SCALE = 1.431, TX = 48.73, TY = 42.03, DIST = 140;

type V = [number, number, number];
type Prim = { kind: "face" | "leg"; pts: V[] };

const CHAIR_MID = 46.4; // the flat chair's centre line, x in logo units

const MODEL: Prim[] = (() => {
  const prims: Prim[] = [];
  const top: V[] = [[-W, H, -D], [W, H, -D], [W, H, D], [-W, H, D]];
  const bottom = top.map(([x, , z]) => [x, H - THICK, z] as V);
  prims.push({ kind: "face", pts: top });
  for (let i = 0; i < 4; i++) {
    const j = (i + 1) % 4;
    prims.push({ kind: "face", pts: [top[i], top[j], bottom[j], bottom[i]] });
  }
  // rear legs run straight on up through the seat's back corners; the band hangs on their tops
  const rearFoot: V = [W + REAR_SPLAY[0] - 0.6, 0, -(D + REAR_SPLAY[1] - 0.6)];
  const rearSeat: V = [W - 0.9, H, -(D - 0.9)];
  const k = (BAND_HI - 0.5) / H;
  const post = rearFoot.map((v, i) => v + (rearSeat[i] - v) * k) as V;
  const bw = post[0] + 2.4, bz = post[2];
  const n = 12;
  const band = (u: number, up: boolean): V => [
    bw * Math.sin(u),
    up ? BAND_HI + 1.4 * Math.cos(u) : BAND_LO,
    bz + 1.6 - 4 * Math.cos(u),
  ];
  for (let i = 0; i < n; i++) {
    const u0 = -Math.PI / 2 + (Math.PI * i) / n, u1 = -Math.PI / 2 + (Math.PI * (i + 1)) / n;
    prims.push({ kind: "face", pts: [band(u0, false), band(u1, false), band(u1, true), band(u0, true)] });
  }
  for (const sx of [-1, 1]) {
    prims.push({ kind: "leg", pts: [[sx * (W + FRONT_SPLAY[0] - 0.6), 0, D + FRONT_SPLAY[1] - 0.6], [sx * (W - 0.9), H - THICK, D - 0.9]] });
    prims.push({ kind: "leg", pts: [[sx * rearFoot[0], 0, rearFoot[2]], [sx * post[0], post[1], post[2]]] });
  }
  return prims;
})();

function project([x, y, z]: V, yaw: number, lift: number) {
  const cy = Math.cos(yaw), sy = Math.sin(yaw);
  [x, z] = [x * cy + z * sy, -x * sy + z * cy];
  const cp = Math.cos(PITCH), sp = Math.sin(PITCH);
  [y, z] = [y * cp - z * sp, y * sp + z * cp];
  const k = DIST / (DIST - z);
  return { x: TX + x * k * SCALE, y: TY - (y + lift) * k * SCALE, z, k };
}

/** The chair at `turn` degrees past its logo pose, lifted `lift` units: flat SVG polygons, one colour. */
function draw(turn: number, lift: number, fill: string) {
  const yaw = YAW + (turn * Math.PI) / 180;
  return MODEL.map(({ kind, pts }) => {
    const p = pts.map((v) => project(v, yaw, lift));
    let poly: [number, number][] = p.map((q) => [q.x, q.y]);
    if (kind === "leg") {
      const [a, b] = p;
      const len = Math.hypot(b.x - a.x, b.y - a.y) || 1;
      const nx = -(b.y - a.y) / len, ny = (b.x - a.x) / len;
      const w0 = 0.62 * a.k * SCALE, w1 = 0.85 * b.k * SCALE; // tapered towards the foot
      poly = [[a.x + nx * w0, a.y + ny * w0], [b.x + nx * w1, b.y + ny * w1], [b.x - nx * w1, b.y - ny * w1], [a.x - nx * w0, a.y - ny * w0]];
    }
    return `<polygon points="${poly.map(([x, y]) => `${x.toFixed(2)},${y.toFixed(2)}`).join(" ")}" fill="${fill}" stroke="${fill}" stroke-width="0.3" stroke-linejoin="round"/>`;
  }).join("");
}

// ---- the motion ----
const MS = 1600;
const WIND_UP = 0.1; // share of the time spent turning back before the spin
// Near the front the flat logo itself moves (a small turn reads fine in 2D:
// its width follows cos); the 3D model takes over only once the chair has
// turned well away, mid-spin, where the motion hides the hand-over. So it
// leaves as the logo and comes back as the logo, exactly.
const FLAT_UNTIL = 14, MODEL_FROM = 24; // degrees from facing front: a quick cut while it turns fast

// The turn: speeding up off the hand, still fast as it comes round to the
// front, then caught there like a swivel hitting its stop: a short spring
// past the front and back (about 7 degrees), settled before it lands.
const CRUISE_END = 0.56, CAUGHT_AT = 342; // fast until here, at this angle
const ACCEL = 1.5; // how the turn speeds up (angle ~ progress^ACCEL)
const WIND = 12; // wind-up, degrees the other way (stays under FLAT_UNTIL: the logo does it)
const ZETA = 0.6, OMEGA = 26; // the catch: damping, stiffness (rad/s)

/** Degrees past the logo pose at t in 0..1: wind-up, a turn that speeds up, a caught stop at 360. */
function angle(t: number) {
  if (t < WIND_UP) return -WIND * Math.sin((Math.PI / 2) * (t / WIND_UP));
  if (t < CRUISE_END) return -WIND + (CAUGHT_AT + WIND) * ((t - WIND_UP) / (CRUISE_END - WIND_UP)) ** ACCEL;
  const speed = ((CAUGHT_AT + WIND) * ACCEL) / ((CRUISE_END - WIND_UP) * (MS / 1000)); // deg/s when caught
  const s = (t - CRUISE_END) * (MS / 1000);
  const wd = OMEGA * Math.sqrt(1 - ZETA * ZETA);
  const a = CAUGHT_AT - 360, b = (speed + ZETA * OMEGA * a) / wd;
  return 360 + Math.exp(-ZETA * OMEGA * s) * (a * Math.cos(wd * s) + b * Math.sin(wd * s));
}

/** Lift (units, up) and squash at t: up as the spin starts, down as it slows, a bump on landing. */
function lift(t: number) {
  const ease = (x: number) => 0.5 - 0.5 * Math.cos(Math.PI * Math.min(1, Math.max(0, x)));
  const y = 6 * (ease((t - WIND_UP) / 0.16) - ease((t - 0.5) / 0.22));
  let squash = 0;
  if (t < WIND_UP) squash = 0.04 * Math.sin(Math.PI * (t / WIND_UP)); // crouch before the lift
  else if (t > 0.72) {
    const land = (t - 0.72) / 0.28;
    squash = 0.07 * Math.exp(-4.5 * land) * Math.cos(10 * land); // lands, then springs back
  }
  return { y, squash };
}

const TONES = { dark: "#FFFFFF", light: "#E0D6CC" }; // the chair's colour: white on the beige home, beige on white pages

export function Logo({ tone = "dark", className = "" }: { tone?: "dark" | "light"; className?: string }) {
  const flat = useRef<SVGPathElement>(null);
  const model = useRef<SVGGElement>(null);
  const running = useRef(false);

  const spin = () => {
    if (running.current || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
    const f = flat.current, m = model.current;
    if (!f || !m) return;
    running.current = true;
    const fill = TONES[tone];
    const start = performance.now();
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / MS);
      const a = angle(t);
      const { y, squash } = lift(t);
      const fromFront = Math.min(Math.abs(a), Math.abs(360 - a));
      const shown = Math.min(1, Math.max(0, (fromFront - FLAT_UNTIL) / (MODEL_FROM - FLAT_UNTIL)));
      // both squash about the feet (wider and lower for a moment) and lift together
      const squashed = `translate(${TX} ${TY}) scale(${1 + squash * 0.6} ${1 - squash}) translate(${-TX} ${-TY})`;
      m.innerHTML = shown > 0 ? draw(a, y, fill) : "";
      m.setAttribute("transform", squashed);
      m.style.opacity = String(shown);
      const turn = Math.cos((a * Math.PI) / 180);
      f.setAttribute("transform", `${squashed} translate(0 ${-y * SCALE}) translate(${CHAIR_MID} 0) scale(${turn} 1) translate(${-CHAIR_MID} 0)`);
      f.style.opacity = String(1 - shown);
      if (t < 1) requestAnimationFrame(step);
      else {
        m.innerHTML = "";
        f.removeAttribute("transform");
        f.style.opacity = "1";
        running.current = false;
      }
    };
    requestAnimationFrame(step);
  };

  return (
    <svg
      viewBox="0 0 93 72"
      fill="none"
      role="img"
      aria-label="RoomTake"
      onPointerDown={spin}
      className={`overflow-visible ${className}`}
    >
      <path ref={flat} d={CHAIR} fill={TONES[tone]} />
      <g ref={model} />
      <g fill="#5E5939">
        {WORDS.map((d) => (
          <path key={d.slice(0, 24)} d={d} />
        ))}
      </g>
    </svg>
  );
}
