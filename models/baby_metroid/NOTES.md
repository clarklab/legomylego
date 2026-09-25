# Baby Metroid Lamp: design notes

The larval Metroid from Super Metroid, about 18 cm across and 32 cm tall on its clear hover
stand, built as a **tap lamp**: press it down and its fangs bite and its nuclei light up;
press again and they go dark. 2,903 pieces in 61 part/colour lines, about 1.7 kg (estimated). Every check passes
except one warning: the Power Functions battery box is rare (last in a set in 2015).

## How the tap works

- **The body slides.** The Metroid sits on a clear tube of stacked round 4x4 plates with a
  round opening (11833). The tube hangs under the base disc and slides down through the
  stand's top. A fixed black axle 16 rises from an anchor in the stand, through the middle of
  the tube and through a guide plate (60474, round pin hole) in the base disc, into the body.
- **The fangs bite.** On top of that axle, inside the body, sits the fang hub, now fixed to
  the stand. Each fang's lever is linked to it by a thick 1x5 link. When the body goes down,
  the levers go down past the hub's pins, and all four fangs swing shut together (from about
  51 degrees open to about 16). Letting go opens them again.
- **The light toggles.** A presser under the tube pushes the green on/off button on top of
  the AAA battery box (88000). That button is push-on, push-off, so the toggle happens inside
  a real LEGO element and no latch mechanism is needed. The button is also the bottom stop:
  the tap travels about 10.5 LDU (4.2 mm); the bridge under the tube would stop it at 16.
- **It springs back.** Two push rods hang from a flange under the tube. Each ends in a
  Technic brick whose pin pulls two Technic rubber belts (85544, medium) down between two
  fixed pins under the bridge, a V that pulls straight up. The belts are pre-stretched
  (about 1.3x), and the stroke only lengthens them about 7%. So they pull almost evenly:
  enough to hold the 1.2 kg body up against the stand's top plate, where the flange stops,
  but only a gentle tap to press. The mechanism check sweeps 24 poses of the press, with
  the body, fangs, links and tube moving, and finds no collisions.
- **Auto-off.** The box switches itself off after 2 hours. Holding the Metroid down for
  3 seconds when switching on disables that (the box's light blinks).

## Wiring (electrics check)

- 2x 8870 light units: one for the two front nuclei, one for the back nucleus. The second
  lamp of the back unit is not used; tuck it under the membrane.
- The leads are laid before the membrane is built. Each plug goes down through the opening in
  the base disc (x 60..100, z 40..100). Under the membrane the leads run above the fixed hub.
  With the body pressed, the gap is still about 4 mm. Below the body they hang down beside
  the tube to the hatch over the battery box's plug. They move with the body, so leave a
  little slack.
- **Assumption**: LEGO lists the 8870 lead as 50 cm. I could not confirm where it splits to
  its two lamps, so each lamp is budgeted 40 cm. The longest run needs about 28 cm.
- To lift the Metroid off its stand, unplug the leads at the hatch first. The tube stays in
  the stand; its top studs just locate the body.

## Decisions

- Dome: Trans-Light Blue. It has the most slope, brick and plate shapes of the pale
  transparent colours.
- Skirt: Coral, with a Dark Red base disc.
- Fangs: White bent beams (32348) with two tooth pieces (41669) each. The spec's Light Nougat
  fang base was dropped; the whole fang is White. At rest they're open; a tap bites.
- Inner body: a Dark Red woven membrane on three black posts. It carries the nuclei and hides
  the mechanism, and stands in for the spec's ribbed "mouth" structure.
- Back nucleus: raised on a hollow chimney of Dark Red bricks, so its lamp's lead runs down
  inside it.

## Known limits

- Not built with real bricks. The checks cover part existence, connections, collisions,
  every insertion, balance, the press sweep and lead lengths. They cannot judge clutch, part
  tolerances, friction, or spring and button forces.
- **The tap needs tuning in real bricks.** I found no published force figures for LEGO rubber
  belts or for the PF button, so the belt count (4) is an estimate. The design makes it easy
  to change: belts hook on pins you can reach through the stand's top before the tiles go on.
- **Sliding fits.** The tube's rings slide over the round 3941 bricks of the axle anchor, and
  their openings are the same 2x2 size. The round tube slides in a square 4x4 opening in the
  stand's top. Both are snug. If they bind, a drop of silicone lubricant (not oil) helps.
- **The presser is 4 mm off the button's centre.** The box puts the button between studs, so
  the presser meets about half of it.
- **Smaller than first planned.** The spec aimed for a body about 25 cm across (30-32 studs).
  The dome was shrunk while the part count was brought down, so the body is about 18 cm
  across. Scaling it back up to 25 cm would take roughly twice the parts. The 18 cm size was
  approved on 2026-09-25.
- The tap version replaced the knob-and-worm fang drive (also on 2026-09-25). The old design
  is in git history.
- Power Functions was discontinued in 2018. The 8870 lights and the 64228 AAA battery box
  (set 88000) have to be bought used. The Powered Up equivalents (the 88005 Light and a
  Powered Up hub) have different plugs and a different box size, and this design has not
  been checked with them.
- Through the faceted dome, the three nuclei read as red glows more than as three separate
  balls.
