#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h}"
export JAVA_HOME="${JAVA_HOME:-/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home}"
export ANDROID_HOME="${ANDROID_HOME:-/Users/win/Library/Android/sdk}"
export GRADLE_USER_HOME="$PWD/android/.tooling/gradle"
export ANDROID_USER_HOME="$PWD/android/.tooling/android-user"
export CARGO_HOME="$PWD/android/.tooling/cargo"
export RUSTUP_HOME="$PWD/android/.tooling/rustup"
export CARGO_TARGET_DIR="$PWD/android/.tooling/rust-target"
export RUSTFLAGS='-C link-arg=-Wl,-z,max-page-size=16384'
[[ -x "$JAVA_HOME/bin/java" && -d "$ANDROID_HOME/platforms/android-36" ]] || { print -u2 'Cần JDK 17, Android SDK 36, Build Tools 36.0.0 và NDK 27.1.12297006. Xem android/README.md.'; exit 1; }
[[ -x "$CARGO_HOME/bin/cargo" ]] || { print -u2 'Cần Rust trong android/.tooling. Xem android/README.md.'; exit 1; }
mkdir -p android/app/src/main/jniLibs/arm64-v8a android/.tooling dist/android
.runtime/bin/python android/scripts/prepare_assets.py ${NANO_MODELS_ROOT:+"$NANO_MODELS_ROOT"}
python3 scripts/prepare_android_voice_previews.py
"$CARGO_HOME/bin/cargo" build --manifest-path android/vendor/sea-g2p/Cargo.toml --locked --release --no-default-features --features capi --target aarch64-linux-android --config "target.aarch64-linux-android.linker=\"$ANDROID_HOME/ndk/27.1.12297006/toolchains/llvm/prebuilt/darwin-x86_64/bin/aarch64-linux-android26-clang\""
cp "$CARGO_TARGET_DIR/aarch64-linux-android/release/libsea_g2p_rs.so" android/app/src/main/jniLibs/arm64-v8a/
print -r -- "sdk.dir=$ANDROID_HOME" > android/local.properties
if [[ ! -f android/.tooling/preview.keystore ]]; then
  "$JAVA_HOME/bin/keytool" -genkeypair -keystore android/.tooling/preview.keystore -storepass android -keypass android -alias soundbooki-preview -keyalg RSA -keysize 2048 -validity 3650 -dname 'CN=Soundbooki Local Test, O=Windi, C=VN'
fi
if [[ -x android/.tooling/gradle-8.13/bin/gradle ]]; then
  android/.tooling/gradle-8.13/bin/gradle -p android :app:assembleDebug --console=plain "$@"
else
  (cd android && ./gradlew :app:assembleDebug --console=plain "$@")
fi
cp android/app/build/outputs/apk/debug/app-debug.apk dist/android/Soundbooki-0.2.7-arm64-test.apk
"$ANDROID_HOME/build-tools/36.0.0/apksigner" verify dist/android/Soundbooki-0.2.7-arm64-test.apk
"$ANDROID_HOME/build-tools/36.0.0/zipalign" -c -P 16 4 dist/android/Soundbooki-0.2.7-arm64-test.apk
shasum -a 256 dist/android/Soundbooki-0.2.7-arm64-test.apk > dist/android/SHA256SUMS.txt
print 'Đã build dist/android/Soundbooki-0.2.7-arm64-test.apk (Android 13+, ARM64; bản thử local).'
