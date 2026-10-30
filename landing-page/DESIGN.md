# Soundbooki landing · Liquid glass

## Current direction: clean graphite · 28/10/2026

The owner corrected the direction toward simple, modern and luxurious, using the supplied Soundbooki app screenshot and a macOS-like visual language as the reference. This is a custom web treatment, not a claim of implementing an official macOS design system. The redesign is targeted: variance 5/10, motion 4/10, density 3/10; existing branding, copy, layout and audio remain.

The opening and hero now use a quiet graphite base, broad low-opacity ambient light, subdued blue accents and restrained shadows. The opening book keeps its existing animation and word effects; ambient notes, spine light and motes are visually quieter. The manuscript uses a readable solid graphite surface, with a thin reflective edge. Glass is limited to controls. No raster backdrop is used. The owner subsequently requested restrained ambient motion; the implementation is described below. Narrow layouts keep the headline to two lines and prevent CTA labels from wrapping.

The earlier cinematic paper-wave backgrounds were exploratory and have been superseded. Originals and prompts remain locally in `design-assets/`; the unused WebP files are excluded from the static build and are no longer referenced or preloaded by the page. Reduced-motion behavior remains unchanged; contrast and reduced-transparency styles follow the graphite palette.

Four decorative phrases rise along the outside rails of the desktop hero, dissolving over about two seconds into the existing local music-note icon. Staggered 15–18 second loops move only 96–112px vertically and at most 20px sideways. The mobile layout uses two smaller fragments above the headline, with 18–20 second loops and 36–40px of travel. These decorations are hidden from assistive technology and never control or start audio. Two broad graphite-blue ambient light layers drift slowly over 22–27 seconds. Only transform and opacity are animated.

A small pause/resume button stops both words and background light without resetting their positions. Motion pauses while the opening overlay is shown, the hero atmosphere is offscreen, the tab is hidden or a dialog is open; a manual pause survives those transitions. Reduced motion suppresses the drifting words and leaves the ambient light static. Reduced transparency removes the extra ambient light, and increased contrast hides the decorative layer.

Validation: source/build checks and local WebKit review at desktop 1280px plus narrow viewport sizes. Screenshots are in `qa/clean-*.png`. No website deployment or native app changes.

Redesigned 24/10/2026 around the owner’s blue-night reference. The old full-page flipbook interaction is replaced with a normal scrolling landing.

- Centered headline and Mac product illustration built in HTML/CSS, with an editorial book cover. The illustration is a product concept; the footer opens the existing actual app screenshot.
- Navy background, luminous blue ribbons, glass controls with thin reflective edges, local Nexa and rounded display fonts.
- Five walkthrough features: free local synthesis, Pro Cloud, ebook reading, offline export, launch combo.
- Local voice samples play only on explicit click. Download metadata and preview installation guidance remain intact.
- Responsive single-column mobile layout; reduced motion, reduced transparency, increased contrast and keyboard focus support.
- No deployment or installer publication in this redesign.

Validation: source and built asset checks passed; browser verified download dialog and explicit sample playback, no browser errors observed; visual review at desktop panel width and 390px mobile iframe.

## Hero with supplied narration · 25/10/2026

The owner supplied `sound_booki_intro_kho_khan.mp3` and then corrected the cue source to `sound_booki_intro_kho_khan_timestamps.json`. The supplied 18.08-second recording and all 63 start/end word cues are used directly. There is no duration stretching or inferred timing calibration. The source cue JSON is preserved in `qa/welcome-timestamps.source.json`; public `welcome-cues.json` contains only duration and the original words/times. The MP3 is copied byte-for-byte.

The hero uses soft typographic reveals instead of a moving object. Each word begins at its supplied audio cue, then lifts only 4px and resolves from a slight blur over 0.95 media seconds. Reveals overlap rather than bouncing or snapping at syllable speed. A restrained glow breathes beneath the arriving words. Before their cue, twelve small musical symbols are distributed evenly across the actual text rows using proportional row allocation and equally spaced horizontal anchors. A single treble clef opens the composition. Tilt and vertical offsets are restrained; staggered 10–12.8 second floating loops keep the symbols alive. Symbols dissolve into text over 0.82–0.95 media seconds. The hidden text retains its layout width, so this does not shift the paragraphs. Original semantic paragraphs remain available to assistive technology; reduced motion shows the full text directly. The marble, shadows and elastic letter deformation have been removed.

Musical notes, soft blooms and spreading rings occur in windows of 2–4 spoken words. The notes drift only about 32px over 4.2–4.6 media seconds; blooms last 4.5 seconds and rings 4.8 seconds. These layers overlap to keep the mood lively but calm. All effect geometry and opacity are derived directly from audio time, including paused and sought frames. At the end of narration, the atmosphere fades over 2.2 seconds.

`HTMLAudioElement.currentTime` drives every visible word and effect; no independent timer or hop rhythm advances the narration. Pause, resume and range seek share the same clock. Narration always plays at 0.95× with pitch preserved; the landing page has no speed control. The owner-provided Piano podcast track 01 loops under the greeting at 18% gain, fades in over 0.5 seconds, and the voice begins one second after the music starts. After the voice ends, the piano continues until its own playback clock reaches 60 seconds, then fades out over three seconds. Pause, hidden-page, offscreen and modal handling also stop the music-only tail. The main toggle can pause/resume that tail, while replay restarts the whole greeting. The track remains a local-only asset. Nothing plays until the user clicks. Hero audio and voice samples are mutually exclusive. Audio pauses offscreen, when the page is hidden or when a modal opens. Reduced motion keeps the text readable and audio controls working, with the visual effects disabled.

Source/build checks passed. Browser playback paused at 10.144213 seconds showed cue “lắng” (10.04–10.36) with visual time 10.144; seeking back to 4.15 seconds showed “âm,” (4.12–4.28). Local preview only; no website or audio publication.

## Loading overlay · 27/10/2026

The open-book contour follows the original artwork. Paper is warm ivory with faint warm-gray lines; the covers/spine are matte charcoal. Paper specular weight is 0.01, with near-zero sheen on the page block and cover. The lower page block is solid and the cover remains a rigid plane. The opening now uses an articulated 3D model from `assets/vendor/book-opening.js`, with solid cover shells, three staggered page layers per side, curved top sheets and a shared spine. Cover/page vertices rotate around that spine; sheet curvature relaxes as the book opens. Camera/light changes expose thickness during the movement. The prior cropped-image rotations have been removed.

The renderer is self-contained WebGL, with no Three.js bundle, external model or textures. Geometry and buffers are built once. GSAP supplies the 2.35-second opening progress; rendering stops when the book is open, aside from resize/replay. Mobile/save-data/low-core mode uses fewer mesh subdivisions, a pixel ratio cap of 1.2 and a 30fps draw ceiling during the opening. Desktop caps pixel ratio at 1.35. `loading-book.svg` remains a static fallback if WebGL is unavailable or lost. The proof clip is `qa/book-opening-motion.mp4`; it is excluded from the web build.

The opening backdrop has restrained layered radial light and six faint music symbols staggered around the edges, away from the book and timed words. Mobile, save-data and low-core mode use four symbols. The symbols float slowly using CSS transforms/opacity, pause with a hidden tab, and are suppressed with reduced motion; the scene's existing audio and word effects remain independent.

The exact owner copy remains “Chào mừng bạn đến với Sound Booki - nơi những trang sách trở thành thanh âm.” Seven short phrase groups start as the opening finishes around 2.4 seconds, become visible over approximately 0.22 seconds, crossfade into notes along their own curves and disappear. Their upward travel is capped at 330px or 78% of the book height, with small individual variation and a viewport-aware limit to avoid flying offscreen. Flights last 3.6–3.96 seconds with a 0.32-second stagger. The hero underneath retains its 63 supplied words, original audio/cues and 0.95x speed.

Reload runs the opening again. The artwork/scene prepare while hidden and wait for two paint frames and a visible tab before starting. Hidden tabs pause the scene. Stable scrollbar space, positioning while the backdrop remains opaque and pausing the main-page ribbon preserve the reveal layout. Bỏ qua, Escape and replay remain available; reduced motion or an artwork load failure reveals the main page directly. Browser/source/build validation does not establish physical-device FPS or public deployment.
