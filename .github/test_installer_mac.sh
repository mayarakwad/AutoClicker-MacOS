#!/bin/bash
# Installs dist/AutoClicker-Setup.pkg from the command line on a GitHub Mac and
# checks what it leaves behind: for me only and for all users with the Dock
# and Desktop choices on (the default), and for all users with them off. Run
# by the macOS build workflow, which has passwordless sudo:
#   bash .github/test_installer_mac.sh dist/AutoClicker-Setup.pkg
# Failures are posted as annotations, which are readable without signing in.
set -uo pipefail

pkg=$1
version=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" dist/AutoClicker.app/Contents/Info.plist)
link="$HOME/Desktop/AutoClicker"
failures=0

check() {  # check "what is checked" command [args...]
    local what=$1
    shift
    if "$@"; then
        echo "  ok: $what"
    else
        echo "::error title=Installer check failed::$what"
        failures=$((failures + 1))
    fi
}

dock_count() {  # how many Dock items point at $1
    defaults read com.apple.dock persistent-apps 2>/dev/null | grep -c -F "$1" || true
}

remove_from_dock() {  # so the next install starts from a clean Dock
    python3 - "$1" <<'PY'
import plistlib, subprocess, sys
dock = plistlib.loads(subprocess.run(["defaults", "export", "com.apple.dock", "-"], capture_output=True, check=True).stdout)
dock["persistent-apps"] = [item for item in dock.get("persistent-apps", []) if sys.argv[1] not in str(item)]
subprocess.run(["defaults", "import", "com.apple.dock", "-"], input=plistlib.dumps(dock), check=True)
PY
    killall Dock 2>/dev/null || true
}

starts() {  # the installed app runs for 10 s without exiting
    local home pid
    home=$(mktemp -d)  # fresh settings; nothing written to the runner's home
    HOME="$home" "$1/Contents/MacOS/AutoClicker" >/dev/null 2>&1 &
    pid=$!
    sleep 10
    if kill -0 "$pid" 2>/dev/null; then
        kill "$pid"
        return 0
    fi
    return 1
}

show_install_log() {  # what the Dock and Desktop scripts said
    local lines
    lines=$(grep "AutoClicker:" /var/log/install.log 2>/dev/null | tail -n 10 | sed 's/%/%25/g' | awk '{printf "%s%%0A", $0}')
    echo "::notice title=Installer scripts ($1)::${lines:-nothing logged}"
}

# $1 name, $2 app path, $3 "on"/"off" for the Dock and Desktop choices,
# then the installer command to run.
test_install() {
    local name=$1 app=$2 extras=$3
    shift 3
    echo "== $name"
    for run in 1 2; do  # the second run is an update over the first
        check "$name: installer run $run succeeds" "$@"
    done
    check "$name: installs $app" test -d "$app"
    check "$name: app version is $version" \
        test "$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" "$app/Contents/Info.plist" 2>/dev/null)" = "$version"
    check "$name: app signature is intact" codesign --verify --deep --strict "$app"
    check "$name: app starts" starts "$app"
    if [ "$extras" = on ]; then
        check "$name: app is in the Dock once (found $(dock_count "$app/"))" test "$(dock_count "$app/")" -eq 1
        check "$name: Desktop link opens $app" test "$(readlink "$link")" = "$app"
        check "$name: the Desktop link belongs to the user" test "$(stat -f %Su "$link" 2>/dev/null)" = "$(id -un)"
    else
        check "$name: app isn't added to the Dock" test "$(dock_count "$app/")" -eq 0
        check "$name: no Desktop link" test ! -L "$link"
    fi
    show_install_log "$name"
    # Clean up for the next install.
    remove_from_dock "AutoClicker.app"
    rm -f "$link"
    sudo rm -rf "$app"
}

echo "== Choices"
choices=$(installer -showChoiceChangesXML -pkg "$pkg" | python3 -c '
import plistlib, sys
print(" ".join(sorted(c["choiceIdentifier"] for c in plistlib.loads(sys.stdin.buffer.read()))))')
check "the installer offers the app, Dock and Desktop choices (got: $choices)" test "$choices" = "app desktop dock"

off=$(mktemp)
cat > "$off" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<array>
    <dict><key>choiceIdentifier</key><string>dock</string><key>choiceAttribute</key><string>selected</string><key>attributeSetting</key><integer>0</integer></dict>
    <dict><key>choiceIdentifier</key><string>desktop</string><key>choiceAttribute</key><string>selected</string><key>attributeSetting</key><integer>0</integer></dict>
</array>
</plist>
XML

test_install "Me-only install" "$HOME/Applications/AutoClicker.app" on \
    installer -pkg "$pkg" -target CurrentUserHomeDirectory
test_install "All-users install" /Applications/AutoClicker.app on \
    sudo installer -pkg "$pkg" -target /
test_install "All-users install without Dock and Desktop" /Applications/AutoClicker.app off \
    sudo installer -pkg "$pkg" -target / -applyChoiceChangesXML "$off"

if [ "$failures" -gt 0 ]; then
    echo "$failures installer check(s) failed."
    exit 1
fi
echo "All installer checks passed."
