# HowItWorks: rehearsal notes

**Gold copied:** `phone-touch` (a phone pinned a gutter from the top, running off
the bottom of a 400 px stage, touch cursor, one app whose screens change).

**What changed:** our product instead of a fitness app. Three scenes in one
phone, played as a carousel with step tabs below the stage:

1. Snap: the camera settles on our real living room (frame_0107), a tap on the
   white shutter, a flash, the photo's thumbnail lands left of the shutter, then
   three SAM finds land on the photo one by one. The one near the right edge
   carries its label on the left, so no label is cut by the screen edge.
2. Pick a style: a tap on Japandi (tile goes ink), the button's label changes
   in its own slot (`States`), a tap on the button.
3. See it, buy it: the divider travels from the right edge to the middle and
   uncovers the restyled room (look 2f76a5db, Japandi Calm), then the Alba sofa's card
   drops in (`Collapse reveal="drop"`) and its Buy is tapped. Holds ~2 s.

Screens swap like one app: the body crossfades with an 8 pt rise; the phone
and its chrome stay. Sizes inside the screen are iPhone points (402 pt wide,
drawn at ~0.7), so app text renders at 11 to 13 px. Stage: 400 x 510, compact
358 x 480 (phone 340 / 326). The page is the ground: transparent stage. The
phone's foot fades out over the last 40 px of the stage; that band holds only
the screen's empty foot (each scene's last control ends 10+ px above it), and
the phone's shadow stays inside the side gutter so the stage never cuts it.

**Poster:** the last scene with the product card in (the payoff); the tabs show
step 3 under reduced motion to match.

**Checked:** 375 px and 1440 px; all three scenes; label clipping; tab tap restarts at that step; the shutter is whole after moving the
camera view up.

**Not checked:** `film.mjs --gate` (the skill's filming script) was not run;
the loop seam (scene 3 back to scene 1) was only watched, not stepped at 60 ms;
the dark theme does not apply (the home page is light only).
