#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
export UV_CACHE_DIR="${TMPDIR:-/private/tmp}/windi-f5-uv"
[[ -x .runtime-f5/bin/python ]] || uv venv --python .runtime/bin/python .runtime-f5
if [[ ! -d .resources/F5-TTS/.git ]]; then
  git clone --filter=blob:none https://github.com/SWivid/F5-TTS.git .resources/F5-TTS
fi
git -C .resources/F5-TTS checkout 2f866649b779881af8bd644e76b9a6d95053da29
uv pip install --python .runtime-f5/bin/python --no-deps -r requirements-f5.lock.txt
uv pip install --python .runtime-f5/bin/python --no-deps .resources/F5-TTS
.runtime/bin/python scripts/setup_f5.py
./scripts/build.sh
