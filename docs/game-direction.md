# The Nation Is Watching — current plan and direction

Updated September 11, 2026. Production planning document, not Steam copy.
Contains the late-game colour reveal, which must stay out of marketing.

This records the direction agreed in the marketing discussion. Features below
are plans unless explicitly described as implemented. Proposed implementation
choices and unresolved questions are labelled separately.

## Identity and constraints

- **Working game title:** The Nation Is Watching. This is the current leading
  name; it does not rename the repository or existing prototype automatically.
- **Domain:** `nationiswatching.com`, purchased by Garrett and confirmed in the
  discussion. Hosting and a public website are not established by that purchase.
- **Target:** a potential Steam game about creating and hosting a television
  talk show in mid-century America, with a career spanning decades.
- **Current production budget:** small and flexible, below the cost of a lawyer
  consultation; not strictly $0. Paid legal review is outside the current budget.
  Targeted spending on tools, voice generation, or a limited performance may be
  considered, but no exact cap or purchase is authorized by this plan. A full
  human voice cast is not assumed affordable. Storefront and hosting costs also
  need to be included in spending decisions.
- **Development approach:** trailer-first development supported by a complete,
  attractive, playable vertical slice. The ambition is a strong trailer and Steam
  page with shareable moments; virality and sales are hypotheses, not forecasts.

## Player fantasy and episode cycle

The player creates a host, develops a show, chooses guests and subjects, and
conducts interviews that affect relationships, the business, and public opinion.
As the career develops, those choices contribute to an alternate Cold War
history. Backstage comedy, seduction, pressure, and danger coexist with earnest
on-air conversation.

The intended cycle is:

1. Customize the host and spend the show's available budget.
2. Furnish the set and arrange hospitality/craft services.
3. Invite guests and choose what to discuss.
4. Conduct the interview and make consequential dialogue choices.
5. See the aftermath through newspapers, personal encounters, and changes to
   relationships and the show's circumstances.
6. Prepare the next episode in the world those decisions helped create.

The management layer includes chairs, coffee tables, backgrounds, and other set
items, plus guest hospitality. Specific prices, stats, sponsor systems, staff
roles, and economic balance have not been decided. Customization should support
personal expression; whether any particular furnishing has mechanical effects
remains a design decision.

## Narrative and historical scope

**Agreed direction:** a large branching story, meaningful choices in the spirit
of Not For Broadcast, and a career that spans decades. The player can steer
public opinion and experience an alternate history shaped partly by the show.
Newspaper interludes are a proposed way to communicate events between scenes.

The discussion included early opposition to the Vietnam War contributing to a
US withdrawal and a different regional outcome, including a communist Thailand.
It also included an anti-gay political trajectory with repression and a changed
early HIV/AIDS trajectory. These are **unvalidated fictional branch ideas**, not
approved historical causal models or final story commitments. Outcomes and
intermediate causes need research and deliberate writing before implementation;
the health-related counterfactual is particularly uncertain. The story should
make the host's contribution and other actors' roles understandable.

**Proposed production method, not yet a settled design:** track accumulated
relationships, reputation, public opinion, and world events; reuse scenes with
meaningful variations and reserve fully separate chapters for major divergences.
This could support a large story without multiplying every dialogue branch into
an entirely independent campaign.

Open questions include the opening year, final year, time jumps, aging, season
length, number of guests, scope of global events, and how much national influence
the host has at each career stage. The goal is not yet a specified geopolitical
simulation or a promise of unlimited procedural dialogue.

## Art direction

**Keep the directly Simpsons-inspired drawing direction.** The creative starting
point is Classic Krusty in the Simpsons episode Bart of Darkness. The developer
wants to retain that influence while creating an original cast and game identity.
Do not silently replace it with an unrelated cartoon aesthetic.

[Adrian Vale's model](../assets/production/adrian/model.png) is the current
original-character reference: angular face, swept dark hair, pencil moustache,
slender adult proportions, dark blazer, and turtleneck. The discussion supports
continuing this direction, with **natural skin tones** for colour assets.

Continue the drawing-based animation approach: saved poses and drawn
transitions, consistent anatomy, expressive silhouettes, and reusable performance
requests. See [the animation plan](game-animation-pipeline.md) and
[production workflow](production-workflow.md).

The existing Krusty/Fromm interview cast demonstrates technology and performance.
It is not the intended original game cast. Public game footage should use the
original cast and appropriate audio rather than present the fan-parody production
as the commercial game's identity.

Recognizable inspiration is an intentional creative choice. Original names and
natural skin tones are not a legal clearance finding. No definitive IP clearance
has been obtained; the developer accepts proceeding without a paid lawyer under
the limited budget. Practical work should focus on distinct characters, their own
personalities and performances, and the game's own title, setting, and stories.
The Cuphead comparison is a creative analogy, not legal precedent for these assets.

## Colour masters and the camera upgrade

**Settled direction:** author the game in colour and apply a consistent grayscale
treatment for the early campaign. Colour appears late in the game, potentially in
the last act, when the player upgrades the show's cameras.

- Character, clothing, furniture, and background masters retain real colours.
- Saved customization retains those colour choices throughout the campaign.
- Review assets in both colour and monochrome; colours that differ must still
  read clearly where gameplay needs separation in grayscale.
- Implement the presentation treatment centrally rather than maintaining
  separate hand-painted colour and monochrome asset libraries.
- The upgrade reveals the familiar cast and set in colour. It is intended as a
  payoff after spending substantial time with the monochrome aesthetic.
- **Do not reveal this feature in the trailer, Steam page, screenshots, or other
  marketing.** Public presentation stays black and white.

The exact colour palette, how hidden colour choices are communicated during
customization, and whether backstage scenes also change when the cameras upgrade
remain open. Offering colour immediately in creator mode was suggested, but has
not been settled and must be considered against preserving the campaign surprise.

This policy is a production target. It does not claim the current grayscale
prototype assets already contain finished colour masters.

## Voice direction

The voice system is **undecided**. The developer is considering invented speech
in the spirit of Simlish, high-quality generated dialogue through ElevenLabs,
and potentially a small amount of human performance. The aim is to support a
large branching story without assuming a full human voice cast is affordable.

The budget permits considering a targeted paid tool or small voice expense;
ElevenLabs and limited trailer/scene acting remain candidates. No subscription,
actor booking, or commercial licence is assumed, and this document does not
authorize a purchase. Existing local tools can support prototypes where appropriate.

**Proposed next comparison:** run the same short conversation using expressive
invented speech and intelligible generated speech, including replaying a branch.
Evaluate personality, timing, reading load, repetition, and the effort needed to
direct, revise, and check the takes. A text-led approach with short vocal reactions
is another candidate, not a decision already made.

Any special trailer performance must set accurate expectations about the game.
If an actor voices a featured game scene, retaining that performance in the
shipped scene is preferable to advertising fully voiced gameplay that will
actually use gibberish. A large wishlist count would inform a future budget
decision, not guarantee a return or automatically authorize spending.

## Trailer-first vertical slice

**Agreed milestone:** a full vertical slice that looks good and can supply honest,
representative footage for a strong trailer and Steam page. The slice needs to
demonstrate the management, hosting, and consequences together.

The developer's proposed trailer sequence is:

1. A quick character-creator shot.
2. Show management and set customization.
3. Inviting a guest.
4. Dialogue about Vietnam, with choices clearly visible.
5. After the show, the host enters the dressing room and finds a femme fatale
   lounging in lingerie.
6. Cut to the host: thrilled.
7. Cut back: she is pointing a pistol at the host.
8. Cut to the host: no longer thrilled.
9. Title card.

Preserve the visual reversal and dry comic timing. The exact edit, duration,
dialogue, cast, and title-card wording are not final. The creator and management
screens and the backstage encounter must come from runnable game content.
The late-game colour upgrade must not appear.

Suggestions made during review, still optional: open with a very brief on-air
moment before customization, and show a consequence of the political choice
before the dressing-room encounter so viewers connect the interview to the danger.

**Proposed slice scope for planning:** two connected episodes with limited host
customization, a small furnishing selection, one hospitality decision, competing
guest invitations, a consequential interview, and an aftermath that visibly
changes episode two. Exact counts and schedule require a development decision.

Evidence to seek before expanding production:

- A player can complete the episode cycle without coaching.
- Choices produce understandable differences in the guest, show, or aftermath.
- The original host and guest look convincing in representative close-ups and
  the studio composition, including actual animation and dialogue playback.
- Normal play can produce the proposed trailer's management and narrative beats.
- Outside players express interest in another episode or a different approach,
  beyond recognizing the Simpsons influence.

No release date, public demo date, Steam page date, price, language set, or festival
commitment is established. Recording and pushing this plan does not authorize
publishing a store page, demo, or trailer, or sending outreach.

## Bonus creator tools

The developer wants a bonus mode that reuses the character creator, studio sets,
animation, and lip sync for podcasters and streamers:

- Create representations of the presenters.
- Import separate audio tracks and assign them to characters.
- Generate an animated video podcast within the game.
- Eventually support a rudimentary VTuber setup: capture a live microphone and
  output lip-synced video with a small delay.

These are intended extensions, not implemented or validated features. The
suggested order is prerecorded multitrack import and video export first, then a
separate latency experiment for live audio. Current offline lip-sync and replay
support does not establish that live microphone capture or broadcasting works.

Keep the creator feature secondary in the game's initial positioning. Whether
it ships at launch, what export options it offers, how overlapping speakers and
camera cuts work, and what live output integration is used remain open.

## Current foundation and immediate work

The repository already has the seated conversation prototype, authored gesture
and posture playback, speech/lip-sync integration for the test cast, production
asset review tools, session saving/replay, and an original Adrian scene study.
Adrian's documented study does not yet provide a finished voiced face rig.
The character creator, show economy, large branching campaign, colour-upgrade
system, and creator-facing audio import/live mode are future work.

Recommended next work, subject to development sequencing:

1. Establish a small original cast and set with colour masters that also work
   in grayscale; define the supported customization pieces before scaling art.
2. Specify and build the first complete episode cycle and its consequences,
   while comparing affordable voice treatments.
3. Connect the next episode, verify the intended trailer beats in play, and use
   outside feedback to decide what deserves further production.

The immediate goal is evidence that the complete fantasy works. The trailer
should be a convincing record of that slice, and the Steam page should describe
the game it can actually become within the available resources.
