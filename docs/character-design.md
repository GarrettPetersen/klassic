# Character design and mouth construction

Every historical guest receives a period-specific character design. Mouth shapes and timing may reuse the shared Simpsons shape vocabulary; the guest's identity, head outline, and facial proportions come from their own portrait. Most guests have skin-colored mouth regions rather than Krusty's outlined gray muzzle.

## Per-character production package

1. Identify the person and interview date. Collect source video frames or documented photographs from that period, including three-quarter views and a speaking expression. Keep source URLs and dates with the character record.
2. Draw a restrained Simpsons-style caricature that preserves the person's distinctive head shape, nose, age, hairstyle, hairline, ears, posture, and period clothing. Add glasses, facial hair, or other features only when supported by the references.
3. Create the wide-shot design and dedicated left/right-facing close-ups from that approved portrait. Share identity and proportions across views.
4. Adapt the shared mouth keys and transitions to the guest's proportions. Recolor the surrounding skin fill to the grayscale luminance of the character's Simpson-yellow skin, remove the muzzle border inside the face, and retain mouth-opening, teeth, and tongue ink. The same general mouth shape can be reused; a separately outlined gray muzzle is not the default guest treatment.
5. Register cels to the fixed upper face for each camera angle. Keep eye and nose placement stable. Have the changing jaw silhouette reveal the clean background underneath. If facial hair or a prop overlaps the mouth, author it as a separate layer with deliberate occlusion.
6. Review a neutral pose, three key speaking shapes, and a short voice-synced animation before producing the interview. Preserve the person’s appearance and manner rather than giving every guest the same generic face or speech motion.

## Current cast

| Character | Reference | State |
| --- | --- | --- |
| Krusty | Original neutral and smiling charts in the [supplied collection](https://archive.org/details/simpsons-mouth-charts) | Nine generated muzzle/jaw cels integrated; Cartoon Studio voice is the user's preferred working take |
| Erich Fromm, 1958 | [Harry Ransom Center interview](https://hrc.contentdm.oclc.org/digital/collection/p15878coll90/id/64/rec/26) | Period portrait and separate nose made; all 81 shared mouth drawings adapted into a guest portrait study. Guest voice and interview-scene placement remain to be produced |
| Current guest sketch | Initial Jenkins concept, without verified portrait likeness | Explicit prototype; must not be relabeled as Fromm or used as a universal guest |

The renderer selects a mouth rig independently for each speaker. A `cels` rig supplies all nine Rhubarb shapes plus its own placement box. The only remaining procedural drawing is the explicitly marked `prototype` guest rig in the earlier test set. Missing production cels fail; they are never replaced with prototype shapes. Moving a character to another angle requires a new cel set and its own registration.

## Krusty shape mapping

Rhubarb's letters identify sound groups; they are not the same naming system as the original production chart.

| Rhubarb | New cel | Chart construction reference |
| --- | --- | --- |
| A | Pressed closed lips: M/B/P | Neutral closed |
| B | Teeth close: consonants/EE | I/J family |
| C | Medium open vowel | C |
| D | Wide open vowel | D/E |
| E | Rounded O | F |
| F | Small OO/W pucker | G/H |
| G | Lower lip against upper teeth: F/V | O |
| H | Tongue raised: L | Open mouth with tongue placement |
| X | Closed resting pose | A |

Generated artwork is in `assets/mouths/`; alpha cels come from the saved green-screen atlas using `klassic.cels.extract_cels`. That step only removes the background and slices the atlas. The clean scene has Krusty's old fixed muzzle removed. Prompts are saved in `prompts/krusty-mouth-cels.txt`; reference scans remain in ignored `inputs/mouth-charts/`.

Fromm’s inspected 1958 reference shows a broad rounded face, thin metal-rimmed glasses, a high forehead and receding combed-back hair, full cheeks, a small mouth, and a rounded chin. These observations are recorded in `episodes/fromm/character-brief.json`. The frame at 1:30 shows Wallace and is not a Fromm portrait reference.

## Transition libraries

Krusty has a complete 36-pair library with two authored in-betweens per pair. Its general mouth shapes and movement can be adapted for guests, including reuse of the drawings after separating the skin and ink layers. Skin tone, placement, proportions, and head silhouette remain character-specific. A new viewing angle requires matching art. See [the production and review workflow](mouth-transitions.md).


## Guest skin and silhouette compositing

User-directed design: most guests use a non-muzzle mouth. The area around the mouth is the same grayscale tone as their Simpson-yellow skin, with no patch outline over the face. The head must still have a black outside contour where skin meets the background.

Author these elements separately for each character and angle:

- A clean plate behind the moving jaw, with its old contour removed.
- A fixed head/face coverage mask, excluding the portion of the jaw that needs to retract.
- Animated mouth-region skin coverage for each key and in-between.
- Interior mouth ink, cavity, teeth, and tongue, separate from the outer muzzle contour.
- Foreground occluders such as the nose, hair, collar, hands, or props.

Composite the fixed head coverage and animated skin coverage into one silhouette. Fill the moving skin with the guest's skin tone, and draw an outside contour only on the exposed boundary of that combined silhouette. A mouth-patch edge lying inside the face gets no outline. A jaw edge extending beyond the fixed face becomes the visible head outline. If the jaw retracts, reveal the clean plate instead of leaving the old chin or outline behind. Foreground layers then cover both fill and outline where appropriate.

Reusing the mouth artwork therefore means separating its surrounding skin fill and outer contour from its interior ink, not deleting all black pixels. The masks distinguish face from background explicitly.

### Fromm portrait study

`assets/characters/fromm/portrait.json` registers a 300×300 mouth canvas at (515,443) on a 1448×1086 portrait. This smaller, inset placement leaves the far cheek visible to the left. The mouth has its own **front** contour even where that edge crosses the far cheek; only the patch's side and back edges disappear into the face. This front-lip contour is distinct from the outer head silhouette.

`klassic.guest` mirrors the existing drawings, recolors their skin, separates patch coverage from ink, and composites a separate foreground nose last. The front outline uses the union of a fitted oval and the moving-mouth rectangle extended to the left edge of the cel. The rectangle is measured from interior ink after excluding the outer muzzle border; all ink within that rectangle or directly left of it is retained. The oval supplies the curved front lip above and below it. Its horizontal center is 100 and radius is 180 on the mirrored 418×418 canvas. Its vertical center follows the mouth opening with an 18-pixel upward offset; its vertical radius is 60% of the measured opening height plus 20 pixels, with a 6-pixel inward feather. Fitting each drawing keeps a closed mouth's rounded chin outside the mask while accommodating open-mouth lip contours. Tests cover the inside lip, horizontal upper-lip connection, and exclusion of rounded chin/top/back ink. The adapted palette retains white teeth and darker tongue/cavity tones.

The portrait and mouthless plate were generated with the saved `prompts/fromm-portrait.txt` and `prompts/fromm-clean-plate.txt`. Separate clean-plate, coverage, and nose PNGs are saved alongside the portrait specification. The current Fromm review is `build/fromm-portrait-review-mouth-guide/index.html`, with nine keys and 72 in-betweens. These are portrait-fit assets; the interview scene still uses its explicitly named prototype guest until Fromm's scene placement is produced.

```sh
python3 -m klassic review-guest assets/characters/fromm/portrait.json --out build/fromm-review-new
```

This creates a local 36-pair flipbook, all 81 portrait composites, and key contact sheets. “Show outline guide” switches each drawing to its source overlay: blue is the oval, orange is the moving-mouth rectangle and its leftward extension, and shading shows the retained outline area. Each historical guest needs a new portrait, nose mask and mouth registration; this Fromm placement is not a universal guest face.
