# Windi Sách Nói — macOS glass

Direction: a focused Mac reading/listening workspace. System typography, graphite text, a restrained blue accent, a translucent sidebar, quiet content surface and floating glass player. Glass belongs to controls and navigation; the document stays readable.

The existing AppKit + WKWebView stack stays. Current command-line SDK is macOS 15.5; use public AppKit vibrancy as the window foundation and local CSS backdrop materials. This is a Liquid Glass inspired interface, not a claim that NSGlassEffectView from SDK 26 is compiled into this build.

Motion: brief spring-like button feedback, content entrance only on actual book/segment changes, a playing equalizer, gentle progress transitions, and an empty-state book illustration. Never reanimate the page on worker progress or playback ticks. Honor system reduced motion, reduced transparency, color scheme and increased contrast; allow local appearance overrides.

Audit of the first UI: flat opaque sidebar, editorial serif headings, hard toolbar separators, text glyph controls, no theme switch, no search, and immediate state changes. Preserve input/edit/play/export IDs and native audio protocol while improving these surfaces.

Pro discovery (2026-10-21, revised): purchase controls appear only inside the Free/Pro dialog and the selected F5 package. Opening the app shows no acquisition card or reader upsell. Selecting a locked F5 choice keeps the current voice and opens its package details before the user chooses to buy. Turbo is retired; Nano remains the default Vietnamese option, with Kitten English and optional Pro F5. Keep existing narration files.

The ui-ux-pro-max purchase-priority UX query did not return a verified match for that specific concern; hierarchy and CTA placement use the skill's general checklist. Its HTML focus guidance applies to the existing WKWebView controls: visible keyboard focus and focus restored when closing purchase. No framework or font changes are needed.

Generation feedback: show a persistent inline status beneath the voice toolbar with preparation, real completed/selected segment counts, a progress bar and cancel. Keep progress across normal renders and book switches; cancelled/error states must not appear complete. Do not show a start toast above the player. Scope/settings panels open beside the upper controls.

Feature discovery (22/10/2026): owner requested five in-app walkthrough pages including Pro launch. Use existing blue accent and system typography, with local feature-specific SVG/CSS illustrations. Auto-show only for an empty library with no walkthrough completion marker; add manual reopen from home and app info. Navigation remains local. Pro details open only from the explicit walkthrough CTA and retain the existing service activation checks. See WALKTHROUGH.md for source mapping and QA.

Walkthrough revision (22/10/2026): owner chose concise benefit order: free on-device PDF/EPUB audiobooks, expressive cloud voice from 10k, ebook reading with saved position, offline audio with relaxing music, five-book 50k launch combo. Use a centered iPad-style illustrated pager with navigation dots, horizontal pointer/trackpad swipes, staged entrance motion, reduced-motion fallback, and final “Nghe Sách của bạn Ngay” import action.

Calm walkthrough (22/10/2026): slow the welcome entrance to 1.25–1.64s with subtle 7–18px movement and soft easing. Play the owner-provided local greeting once with Piano podcast Bài 01 underneath (voice 80%, music 40%); music eases in and fades out on close. Header sound toggle persists locally. Paging never restarts audio; narration/music settings and assets remain separate. Respect reduced motion as before.

Soundbooki identity (22/10/2026): use the owner's `media-kit/logo/logo.png`, `typo.png` and `background.png`. `scripts/Icon.swift` removes their transparent export margins when composing the derived assets; it never changes the originals. The macOS icon has one rounded tile with the supplied background extending to its edge and a large book mark, without the previous extra inset. Keep the transparent outer Dock alignment canvas. In the sidebar, app info, walkthrough and retained legacy payment header, pair the transparent book mark with the supplied Soundbooki wordmark using `ui/brand.css`; the wordmark supplies the accessible brand name and the adjacent mark is decorative. The app's bundle identity, library and legacy licenses remain stable. Rebuild derived assets and all ICNS sizes with `./scripts/build.sh`.

### Banner sách dựng bằng code · 23/10/2026

Banner ra mắt Mac dùng 5 jacket HTML/CSS riêng, chữ thật và các cảnh SVG inline trong `ui/index.html` / `ui/launch-offer.css`. Không còn tải ảnh raster cho banner. Cụm sách chiếm khoảng 80% vùng minh họa; banner giữ dải ngang gọn (128–144px trên Mac), giữ nút và giá riêng khỏi tranh. Mỗi bìa khóa aspect-ratio 2:3; cụm sách có giới hạn kích thước, không làm tăng chiều cao khi cửa sổ rộng. Các bìa là minh họa trang trí, không phải danh mục sách được cấp kèm combo.

Android dùng `ReadingBanner` và `BannerBooksView` native Java/Canvas, đo theo chiều rộng thực, luôn giữ bố cục ngang gọn và giới hạn chiều cao vùng minh họa. Cùng màu bìa, tựa và đường nét vector; không chia sẻ runtime hay kích hoạt giá combo Mac trên Android. Nút Android là thêm sách; bảng giá/luồng mua Android vẫn ở phạm vi riêng.
