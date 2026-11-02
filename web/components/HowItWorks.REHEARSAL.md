# HowItWorks: rehearsal notes

**Gold copied:** `phone-touch` (a phone pinned a gutter from the top, running off
the bottom of a 400 px stage, touch cursor, one app whose screens change).

**What changed:** our product instead of a fitness app. Three scenes in one
phone, played as a carousel with step tabs below the stage:

1. Film: the camera pans across our real living room (frame_0107); four SAM
   finds land as they come into view. Each find leaves before the pan takes it
   out, and the one near the right edge carries its label on the left, so no
   label is ever cut by the screen edge (checked every 100 ms over the scene).
2. Pick a style: a tap on Japandi (tile goes ink), the button's label changes
   in its own slot (`States`), a tap on the button.
3. See it, buy it: the divider travels from the right edge to the middle and
   uncovers the restyled room (look 4c3e4a22), then the Denton rug's card
   drops in (`Collapse reveal="drop"`) and its Buy is tapped. Holds ~2 s.

Screens swap like one app: the body crossfades with an 8 pt rise; the phone
and its chrome stay. Sizes inside the screen are iPhone points (402 pt wide,
drawn at ~0.7), so app text renders at 11 to 13 px. Stage: 400 x 470, compact
358 x 440 (phone 340 / 326). The page is the ground: transparent stage.

**Poster:** the last scene with the product card in (the payoff); the tabs show
step 3 under reduced motion to match.

**Checked:** 375 px and 1440 px; all three scenes; label clipping during the
pan; tab tap restarts at that step; the shutter is whole after moving the
camera view up.

**Not checked:** `film.mjs --gate` (the skill's filming script) was not run;
the loop seam (scene 3 back to scene 1) was only watched, not stepped at 60 ms;
the dark theme does not apply (the home page is light only).
