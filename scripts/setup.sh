#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
export UV_CACHE_DIR="${TMPDIR:-/private/tmp}/windi-sach-uv"
command -v uv >/dev/null || { echo 'Cần uv để tạo runtime riêng: https://docs.astral.sh/uv/getting-started/installation/'; exit 1; }
[[ -x .runtime/bin/python ]] || uv venv --python 3.12 .runtime
uv pip install --python .runtime/bin/python -r requirements.lock.txt
.runtime/bin/python scripts/prepare.py "$@"
./scripts/build.sh
