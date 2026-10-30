#!/bin/zsh
# Read-only checks of the adjacent test app. No security settings are changed.
set -u
SCRIPT_DIR="${0:A:h}"
APP="$SCRIPT_DIR/WindiSachNoi.app"
if [[ ! -d "$APP" ]]; then
  print 'Đặt tệp này cạnh WindiSachNoi.app rồi chạy lại.'
  read -r '?Nhấn Enter để đóng.'
  exit 1
fi
REPORT="$(/usr/bin/mktemp /private/tmp/WindiSachNoi-diagnostic.XXXXXX)"
{
  print 'Windi Sách Nói — chẩn đoán mở app (không chứa mã máy/Keychain/sách)'
  /bin/date -u
  /usr/bin/sw_vers
  /usr/bin/uname -m
  print '\n--- Bundle ---'
  /usr/bin/plutil -lint "$APP/Contents/Info.plist"
  for field in CFBundleVersion CFBundleExecutable CFBundleSupportedPlatforms LSMinimumSystemVersion; do
    print "$field:"
    /usr/bin/plutil -extract "$field" json -o - "$APP/Contents/Info.plist"
    print
  done
  print '\n--- Quyền và kiến trúc ---'
  /bin/ls -l "$APP/Contents/MacOS/WindiSachNoi"
  /usr/bin/file "$APP/Contents/MacOS/WindiSachNoi"
  print '\n--- Chữ ký ---'
  /usr/bin/codesign --verify --deep --strict --verbose=2 "$APP"
  print "codesign exit: $?"
  print '\n--- Thuộc tính bảo mật (chỉ tên) ---'
  /usr/bin/xattr "$APP"
  print '\n--- Gatekeeper ---'
  /usr/sbin/spctl --assess --type execute --verbose=4 "$APP"
  print "spctl exit: $?"
  print '\n--- Thử mở qua Launch Services ---'
  /usr/bin/open -n "$APP"
  print "open exit: $?"
  print '\nGatekeeper có thể từ chối app ad-hoc. Báo cáo này không tự bỏ chặn hoặc sửa chữ ký.'
} > "$REPORT" 2>&1
/usr/bin/open -a TextEdit "$REPORT"
print "Đã tạo báo cáo: $REPORT"
print 'Gửi nội dung báo cáo này để kiểm tra lỗi trên Mac đang dùng.'
