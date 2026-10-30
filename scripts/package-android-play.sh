#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
JAVA_BIN="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}/bin"
KEY_DIR="$PWD/android/.tooling/play-upload"
OUTPUT="$PWD/dist/android/Soundbooki-0.2.7-play-fixed.aab"
[[ -f "$KEY_DIR/soundbooki-upload.p12" && -f "$KEY_DIR/password.txt" ]] || { print -u2 'Thiếu khóa upload hoặc mật khẩu.'; exit 1; }
./scripts/build.sh --android :app:bundleRelease "$@"
cp android/app/build/outputs/bundle/release/app-release.aab "$OUTPUT"
# Fail closed if owner-local recordings enter the release bundle.
if unzip -Z1 "$OUTPUT" | rg -q '^base/assets/(voice-previews/|welcome/welcome\.wav$)'; then
  print -u2 'Gói vẫn chứa bản ghi chỉ dùng nội bộ.'; exit 1
fi
"$JAVA_BIN/jarsigner" -keystore "$KEY_DIR/soundbooki-upload.p12" -storetype PKCS12 -storepass:file "$KEY_DIR/password.txt" "$OUTPUT" soundbooki-upload
"$JAVA_BIN/jarsigner" -verify "$OUTPUT"
[[ -f android/.tooling/bundletool-all-1.18.1.jar ]] || { print -u2 'Thiếu bundletool để kiểm tra gói Play.'; exit 1; }
mkdir -p .qa/android-play
"$JAVA_BIN/java" -jar android/.tooling/bundletool-all-1.18.1.jar build-apks --bundle="$OUTPUT" --output=.qa/android-play/Soundbooki.apks --overwrite --ks=android/.tooling/preview.keystore --ks-key-alias=soundbooki-preview --ks-pass=pass:android --key-pass=pass:android
shasum -a 256 "$OUTPUT" > "$OUTPUT.sha256"
print "Đã tạo $OUTPUT"
