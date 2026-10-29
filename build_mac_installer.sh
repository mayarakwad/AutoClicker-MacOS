#!/bin/bash
# Builds dist/AutoClicker-Setup.pkg, the Mac installer for dist/AutoClicker.app,
# from mac_installer/. Run on a Mac (it runs build_mac.sh first if the app
# isn't built yet):
#   bash build_mac_installer.sh
set -euo pipefail
cd "$(dirname "$0")"

if [ ! -d dist/AutoClicker.app ]; then
    bash build_mac.sh
fi
# The installer's version is the app's (from version_info.txt, via build_mac.sh).
version=$(/usr/libexec/PlistBuddy -c "Print CFBundleShortVersionString" dist/AutoClicker.app/Contents/Info.plist)

work=build/mac_installer
rm -rf "$work"
mkdir -p "$work/root" "$work/packages" "$work/resources"

echo "Building the installer..."
# The app goes to Applications on the disk and in the domain the user picks.
ditto dist/AutoClicker.app "$work/root/AutoClicker.app"
pkgbuild --quiet --analyze --root "$work/root" "$work/app.plist"
# Without this, Installer would update a copy it finds elsewhere on the Mac
# instead of installing where the user chose.
plutil -replace 0.BundleIsRelocatable -bool NO "$work/app.plist"
pkgbuild --quiet --root "$work/root" --component-plist "$work/app.plist" \
    --identifier com.autoclicker.pkg.app --version "$version" --install-location /Applications \
    "$work/packages/app.pkg"

# Add to Dock and Desktop link: one script-only package per choice.
for choice in dock desktop; do
    mkdir -p "$work/scripts-$choice"
    cp mac_installer/scripts/common.sh "$work/scripts-$choice/"
    cp "mac_installer/scripts/${choice}_postinstall" "$work/scripts-$choice/postinstall"
    chmod +x "$work/scripts-$choice/postinstall"
    pkgbuild --quiet --nopayload --scripts "$work/scripts-$choice" \
        --identifier "com.autoclicker.pkg.$choice" --version "$version" "$work/packages/$choice.pkg"
done

sed "s/@VERSION@/$version/g" mac_installer/Distribution.xml > "$work/Distribution.xml"
cp mac_installer/conclusion.html "$work/resources/"
productbuild --quiet --distribution "$work/Distribution.xml" --package-path "$work/packages" \
    --resources "$work/resources" dist/AutoClicker-Setup.pkg

echo
echo "Done: dist/AutoClicker-Setup.pkg ($version)"
