# Portable macOS Unicode signature regression — 2026-10-28

Build 21 passed `codesign --verify --deep --strict` on the development APFS
volume but failed the same check after `hdiutil create -fs HFS+` and mounting
the resulting read-only image. Codesign reported added/missing resources for
18 VieNeu sample files with Vietnamese names under
`Contents/Resources/App/.runtime/lib/python3.12/site-packages/vieneu/assets/samples`.
The displayed filenames were identical; their Unicode spellings differed.

`scripts/package_macos.py` now normalizes all bundle component names to NFD
before signing. Canonically equivalent APFS renames use an intermediate ASCII
name to ensure the stored spelling actually changes. Text contents, model
checksums, source books and user data are unchanged.

Build 22 validation:

- Built through `scripts/build.sh`; ad-hoc signing verified locally.
- DMG checksum verified on mount; `codesign --verify --deep --strict` also
  passed on `/Volumes/WindiSachNoi-Test22/WindiSachNoi.app` (HFS+, read-only).
- Native UI opened from the mounted image with a fresh `.qa` library.
- `tests/portable_integration.py` against that mounted image passed: fixture
  EPUB import, real Nano and Kitten synthesis, WAV/M4A/web ZIP export, restart
  and settings/cache restoration. Report: `.qa/portable-integration/report.json`.
- Earlier audit of the same runtime found no external absolute dylib loads
  among 328 thin arm64 Mach-O files; their minimum OS versions were 11–15.

This establishes a reproducible transfer/signature defect and verifies its
repair locally. It does not establish the exact failure on the second Mac:
its OS was reported as macOS 26, but no destination diagnostic report was
available. This is an internal ad-hoc candidate, not a notarized public release.

The DMG includes `Kiem-tra-Mac.command`, sourced from
`scripts/diagnose-macos.command`. It checks the adjacent app without removing
quarantine, re-signing, changing security settings, or reading library/Keychain
data. Use a destination report if opening still fails.
