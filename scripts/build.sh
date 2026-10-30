#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
if [[ "${1:-}" == "--android" ]]; then
  exec ./scripts/build-android.sh "${@:2}"
fi
mkdir -p .build dist/'Windi Sách Nói.app'/Contents/{MacOS,Resources}
.runtime/bin/python scripts/music.py
export CLANG_MODULE_CACHE_PATH="${TMPDIR:-/private/tmp}/windi-sach-clang"
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/Extract.swift -o .build/windi-extract
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/Cover.swift -o .build/windi-cover
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/EbookAssets.swift -o .build/windi-ebook-assets
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/License.swift -o .build/windi-license
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/CloudKeychain.swift -o .build/windi-cloud-keychain
swiftc -O -target arm64-apple-macosx15.0 -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" native/App.swift native/PageTurn/EbookTurnBridge.swift native/SourceReader.swift native/Payment.swift native/Import.swift native/Music.swift native/Welcome.swift native/NarrationQueue.swift -o 'dist/Windi Sách Nói.app/Contents/MacOS/WindiSachNoi'
swiftc -O -module-cache-path "${TMPDIR:-/private/tmp}/windi-sach-swift" scripts/Icon.swift -o .build/make-icon
.build/make-icon .build/WindiSachNoi.iconset media-kit/logo ui/brand
python3 scripts/package_icon.py .build/WindiSachNoi.iconset 'dist/Windi Sách Nói.app/Contents/Resources/WindiSachNoi.icns'
mkdir -p ui/brand
cp .build/WindiSachNoi.iconset/icon_256x256@2x.png ui/brand/app-icon.png
python3 - <<'PY'
import json,pathlib,plistlib
p=pathlib.Path.cwd()
version=json.loads((p/'app-version.json').read_text())
info={'CFBundleName':'Windi Sách Nói','CFBundleDisplayName':'Windi Sách Nói','CFBundleIdentifier':'studio.windi.sachnoi.local','CFBundleVersion':version['build'],'CFBundleShortVersionString':version['version'],'CFBundleExecutable':'WindiSachNoi','CFBundleIconFile':'WindiSachNoi','CFBundlePackageType':'APPL','CFBundleInfoDictionaryVersion':'6.0','CFBundleDevelopmentRegion':'vi','CFBundleSupportedPlatforms':['MacOSX'],'NSPrincipalClass':'NSApplication','LSMinimumSystemVersion':'15.0','NSHighResolutionCapable':True,'WindiProjectRoot':str(p)}
(p/'dist/Windi Sách Nói.app/Contents/Info.plist').write_bytes(plistlib.dumps(info))
(p/'dist/Windi Sách Nói.app/Contents/PkgInfo').write_bytes(b'APPL????')
PY
mkdir -p 'dist/Windi Sách Nói.app/Contents/Resources/Licenses'
cp -R licenses/. 'dist/Windi Sách Nói.app/Contents/Resources/Licenses/'
mkdir -p 'dist/Windi Sách Nói.app/Contents/Resources/Licenses/GulLabs-Flipbook/source'
cp -R ui/vendor/gul-flipbook/source/. 'dist/Windi Sách Nói.app/Contents/Resources/Licenses/GulLabs-Flipbook/source/'
codesign --force --sign - 'dist/Windi Sách Nói.app'
if [[ "${WINDI_SKIP_REGISTRATION:-0}" != "1" ]]; then
  /System/Library/Frameworks/CoreServices.framework/Frameworks/LaunchServices.framework/Support/lsregister -f "dist/Windi Sách Nói.app"
fi
echo 'Đã build dist/Windi Sách Nói.app (bản chạy local từ project).'
