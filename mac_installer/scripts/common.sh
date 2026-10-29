# Shared by the Add to Dock and Desktop link postinstall scripts. Installer
# runs them as root for an all-users install and as the user for a "me only"
# install. They act for the user who is installing, and never fail the
# install: if something goes wrong they log it (to /var/log/install.log) and
# exit 0.
#
# Installer passes the install target as $3: / (all users), the user's home
# folder (me only), or another disk's mount point.

log() { echo "AutoClicker: $*"; }

# The user to act for: whoever is signed in at the screen for an all-users
# install, or the user running Installer for a "me only" install.
if [ "$(id -u)" -eq 0 ]; then
    USER_NAME=$(stat -f %Su /dev/console)
else
    USER_NAME=$(id -un)
fi
case "$USER_NAME" in
    "" | root | _mbsetupuser) log "nobody is signed in; skipping"; exit 0 ;;
esac
USER_HOME=$(dscl . -read "/Users/$USER_NAME" NFSHomeDirectory 2>/dev/null | awk '{print $2}')
[ -n "$USER_HOME" ] || USER_HOME="/Users/$USER_NAME"

# Runs a command as that user, in their login session (so `defaults` and
# `killall Dock` reach their Dock, not root's).
as_user() {
    if [ "$(id -u)" -eq 0 ]; then
        launchctl asuser "$(id -u "$USER_NAME")" sudo -u "$USER_NAME" "$@"
    else
        "$@"
    fi
}

# The app this install put in place, looked up where each kind of install puts it.
APP=""
for candidate in "${3%/}/Applications/AutoClicker.app" "$USER_HOME/Applications/AutoClicker.app" /Applications/AutoClicker.app; do
    if [ -d "$candidate" ]; then
        APP=$candidate
        break
    fi
done
if [ -z "$APP" ]; then
    log "can't find the installed AutoClicker.app; skipping"
    exit 0
fi
