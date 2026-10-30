# GulLabs flipbook core

Unmodified source of `@gullabs/flipbook-core` 3.2.2 from
https://github.com/gul-labs/flipbook/tree/3fb7192c02ecca559d67192d15a1479fd7cf3af8/packages/core/src
is included in `source/`. The app adapter lives separately in `ui/flipbook-turn.js`.
Only the HTML engine is bundled; no React, remote assets or runtime dependencies.

License and upstream notices: `licenses/GulLabs-Flipbook/` at the project root
(also inside the app's Resources/Licenses). Source is provided alongside the
bundle in this folder, under MPL-2.0. The enclosing application's license is
separate. No engine source files have been modified.

To rebuild with an installed esbuild:

    node scripts/build_flipbook.cjs /absolute/path/to/esbuild

The normal `./scripts/build.sh` needs no Node tooling or network.
