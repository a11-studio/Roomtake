"use client";

import { useMemo, useRef, useState } from "react";
import { Collapse, Phone, Stage, States, useReducedMotion, type Act } from "@/stageshow/kit";
import "./how-it-works.css";

// The home page's "how it works", as one phone that plays the three steps.
//
// 1 Snap:            the camera settles on our real living room, a tap on the
//                    shutter, a flash; SAM's finds land on the photo
// 2 Pick a style:    a tap on Japandi; the button takes the style's name; a tap
// 3 See it, buy it:  the divider travels to the middle and uncovers the
//                    restyled room; the real sofa in it rises in with its price
//
// Real strings: four object names, four style names, the button, the look's
// title, the product and its price. The rest is image or shape.
// Scenes swap like screens in one app: the body crossfades, the phone stays.

type Step = 0 | 1 | 2;
type S = {
  step: Step;
  pan: boolean; // the camera has settled on the room
  flash: boolean; // the shutter's flash
  shot: boolean; // the photo is taken (its thumbnail is in)
  finds: number; // bitmask: which finds are showing
  picked: boolean; // Japandi tapped
  named: boolean; // the button says "Show my room in Japandi"
  reveal: number; // divider position, % from the left (100 = all before)
  product: boolean; // the sofa's card is in
};

export const STEPS = [
  { title: "Snap", text: "Take 1–3 photos of your room from its best corners." },
  { title: "Pick a style", text: "Scandinavian, Japandi, Art Deco and more." },
  { title: "See it, buy it", text: "Your room restyled with real pieces you can order." },
] as const;

/** Length of each scene; the tabs' progress runs on the same clock. */
export const SCENE_MS = [5000, 4600, 6200] as const;

const START: S = { step: 0, pan: false, flash: false, shot: false, finds: 0, picked: false, named: false, reveal: 100, product: false };
const POSTER: S = { ...START, step: 2, reveal: 50, product: true, picked: true, named: true, pan: true, shot: true, finds: 0b111 };
const REST = { x: 380, y: 470 };

// Where the finds sit on the photo (fractions of frame_0107, from SAM's boxes);
// all three are in the settled frame. They land one by one after the shot.
const FINDS = [
  { label: "coffee table", x: 0.55, y: 0.74 },
  { label: "sofa", x: 0.7, y: 0.6 },
  { label: "side table", x: 0.9, y: 0.86, flip: true },
];
const FIND_GAP = 450;

const STYLES = [
  { name: "Scandinavian", swatches: ["#efe8dc", "#c9a57d", "#9aa7a2"] },
  { name: "Japandi", swatches: ["#e6ddcf", "#8c7a64", "#3b3631"] },
  { name: "Art Deco", swatches: ["#1f4d3e", "#c9a34e", "#1e2a44"] },
  { name: "Mid-Century", swatches: ["#8a5a3b", "#d4a23a", "#6b7f4e"] },
];

function makeScript(start: Step, onStep: (s: Step) => void) {
  const scenes: Record<Step, (a: Act<S>) => Promise<void>> = {
    0: async (a) => {
      await a.snap({ pan: false, flash: false, shot: false, finds: 0 });
      a.set({ step: 0 });
      onStep(0);
      await a.wait(250);
      a.set({ pan: true }); // framing the shot
      await a.wait(1300);
      await a.click("shutter");
      a.put({ flash: true });
      await a.wait(120);
      a.put({ flash: false, shot: true });
      await a.wait(450);
      for (let i = 0; i < FINDS.length; i++) {
        a.put((s) => ({ finds: s.finds | (1 << i) }));
        await a.wait(FIND_GAP);
      }
      await a.wait(SCENE_MS[0] - 250 - 1300 - 900 - 120 - 450 - FINDS.length * FIND_GAP);
    },
    1: async (a) => {
      await a.snap({ picked: false, named: false });
      a.set({ step: 1 });
      onStep(1);
      await a.wait(1000);
      await a.click("japandi");
      a.put({ picked: true });
      await a.wait(300);
      a.put({ named: true });
      await a.wait(1300);
      await a.click("cta");
      await a.wait(SCENE_MS[1] - 1000 - 300 - 1300 - 900);
    },
    2: async (a) => {
      await a.snap({ reveal: 100, product: false });
      a.set({ step: 2 });
      onStep(2);
      await a.wait(700);
      a.set({ reveal: 50 });
      await a.wait(1500);
      a.put({ product: true });
      await a.wait(1400);
      await a.click("buy");
      await a.wait(SCENE_MS[2] - 700 - 1500 - 1400 - 400);
    },
  };
  const order = [0, 1, 2, 0, 1, 2].slice(start, start + 3) as Step[];
  return async (a: Act<S>) => {
    for (const step of order) await scenes[step](a);
  };
}

function Snap({ s }: { s: S }) {
  return (
    <div className="how-film">
      <div className="how-film__pan" data-pan={s.pan || undefined}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/demo/room.jpg" alt="" className="how-film__img" />
        {FINDS.map((f, i) => (
          <span
            key={f.label}
            className="how-find"
            data-on={(s.finds >> i) & 1 || undefined}
            data-flip={f.flip || undefined}
            style={{ left: `${f.x * 100}%`, top: `${f.y * 100}%` }}
          >
            <span className="how-find__dot" />
            <span className="how-find__label">{f.label}</span>
          </span>
        ))}
      </div>
      <span className="how-film__flash" data-on={s.flash || undefined} />
      <span className="how-film__thumb" data-on={s.shot || undefined}>
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/demo/room.jpg" alt="" />
      </span>
      <span className="how-film__shutter" data-target="shutter" />
    </div>
  );
}

function Pick({ s }: { s: S }) {
  return (
    <div className="how-pick">
      <div className="how-label">Style</div>
      <div className="how-tiles">
        {STYLES.map((st) => {
          const on = s.picked && st.name === "Japandi";
          return (
            <span
              key={st.name}
              className="how-tile"
              data-on={on || undefined}
              data-target={st.name === "Japandi" ? "japandi" : undefined}
            >
              <span className="how-swatches">
                {st.swatches.map((c) => (
                  <span key={c} style={{ background: c }} />
                ))}
              </span>
              <span className="how-tile__name">{st.name}</span>
            </span>
          );
        })}
      </div>
      <span className="how-cta" data-target="cta">
        <States
          value={s.named ? "named" : "any"}
          states={{ any: "Surprise me with a style", named: "Show my room in Japandi" }}
        />
      </span>
    </div>
  );
}

function See({ s }: { s: S }) {
  return (
    <div className="how-see">
      <div className="how-label">Your room, restyled</div>
      <div className="how-title">Japandi Calm</div>
      <div className="how-compare">
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/demo/room-japandi.jpg" alt="" />
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img src="/demo/room.jpg" alt="" style={{ clipPath: `inset(0 ${100 - s.reveal}% 0 0)` }} className="how-compare__before" />
        <span className="how-compare__line" style={{ left: `${s.reveal}%` }} data-on={s.reveal < 100 || undefined} />
      </div>
      <Collapse open={s.product} reveal="drop">
        <div className="how-product">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img src="/demo/sofa.jpg" alt="" />
          <span className="how-product__text">
            <span className="how-product__name">Alba 2-seater sofa</span>
            <span className="how-product__price">€799</span>
          </span>
          <span className="how-buy" data-target="buy">
            Buy
          </span>
        </div>
      </Collapse>
    </div>
  );
}

export function HowItWorks() {
  const [start, setStart] = useState<Step>(0);
  const [run, setRun] = useState(0);
  const [playing, setStep] = useState<Step>(0);
  // Reduced motion: the stage shows its poster (the last step), so do the tabs
  const step: Step = useReducedMotion() ? 2 : playing;
  const [tick, setTick] = useState(0); // restarts the active tab's progress
  const onStep = useRef((s: Step) => {
    setStep(s);
    setTick((t) => t + 1);
  });
  // a new script per start step; the Stage remounts with it (key={`run-${run}`})
  const script = useMemo(() => makeScript(start, (s) => onStep.current(s)), [start]);

  const jump = (i: Step) => {
    setStart(i);
    setStep(i);
    setTick((t) => t + 1);
    setRun((r) => r + 1); // a tap on a tab restarts the demo at that step
  };

  return (
    <div className="how-host">
      <Stage<S>
        key={`run-${run}`}
        width={400}
        height={510}
        compact={{ below: 400, width: 358, height: 480 }}
        initial={{ ...START, step: start }}
        poster={POSTER}
        script={script}
        cursor={{ at: REST, style: "touch" }}
        className="how"
      >
        {(s, _rect, layout) => (
          <Phone width={layout === "compact" ? 326 : 340} dark={s.step === 0} className="how-phone">
            <div className="how-screen" data-on={s.step === 0 || undefined}>
              <Snap s={s} />
            </div>
            <div className="how-screen how-screen--light" data-on={s.step === 1 || undefined}>
              <Pick s={s} />
            </div>
            <div className="how-screen how-screen--light" data-on={s.step === 2 || undefined}>
              <See s={s} />
            </div>
          </Phone>
        )}
      </Stage>

      <ol className="how-tabs">
        {STEPS.map((st, i) => (
          <li key={st.title}>
            <button
              onClick={() => jump(i as Step)}
              className="how-tab"
              data-state={i < step ? "done" : i === step ? "now" : "next"}
              aria-current={i === step ? "step" : undefined}
            >
              <span className="how-tab__bar">
                <span key={i === step ? tick : "rest"} style={{ animationDuration: `${SCENE_MS[i]}ms` }} />
              </span>
              <span className="how-tab__title">
                <span className="how-tab__num">{i + 1}</span>
                {st.title}
              </span>
            </button>
          </li>
        ))}
      </ol>
      <p key={`caption-${step}`} className="how-caption page-in">
        {STEPS[step].text}
      </p>
    </div>
  );
}
