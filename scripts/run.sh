#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
[[ -x 'dist/Windi Sách Nói.app/Contents/MacOS/WindiSachNoi' ]] || ./scripts/build.sh
app="$PWD/dist/Windi Sách Nói.app"
/System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "$app"
open -n "$app"
