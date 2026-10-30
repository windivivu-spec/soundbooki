#!/bin/zsh
set -euo pipefail
cd "${0:A:h:h:h}"
adb=/Users/win/Library/Android/sdk/platform-tools/adb
"$adb" install -r dist/android/Soundbooki-0.1.1-arm64-test.apk
"$adb" install -r android/app/build/outputs/apk/androidTest/debug/app-debug-androidTest.apk
"$adb" shell mkdir -p /sdcard/Android/data/windi.soundbooki/files/qa
"$adb" push android/qa/selected-203-page.pdf /sdcard/Android/data/windi.soundbooki/files/qa/selected-203-page.pdf
"$adb" shell svc wifi disable
"$adb" shell svc data disable
"$adb" shell am instrument -w -r windi.soundbooki.test/androidx.test.runner.AndroidJUnitRunner > android/qa/chapter-all-tests.txt
