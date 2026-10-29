# Shared by the Add to Dock and Desktop link postinstall scripts. Installer
# runs them as root for an all-users install (or one on another disk), with
# the target disk as $3, and as the user for a "me only" install. They act for
# the user signed in at the screen (all users) or the user installing (me
# only), and never fail the install: if something goes wrong they log it (to
# /var/log/install.log) and exit 0.

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
USER_HOME=$(dscacheutil -q user -a name "$USER_NAME" 2>/dev/null | sed -n 's/^dir: //p' | head -n 1)
case "$USER_HOME" in
    /*) ;;
    *) USER_HOME="/Users/$USER_NAME" ;;
esac

# Runs a command as that user, in their login session (so `defaults` and
# `killall Dock` reach their Dock, not root's).
as_user() {
    if [ "$(id -u)" -eq 0 ]; then
        launchctl asuser "$(id -u "$USER_NAME")" sudo -u "$USER_NAME" "$@"
    else
        "$@"
    fi
}

# The app this install put in place. Only that one: never another copy.
if [ "$(id -u)" -eq 0 ]; then
    APP="${3%/}/Applications/AutoClicker.app"  # all users (/) or another disk (/Volumes/...)
else
    APP="$USER_HOME/Applications/AutoClicker.app"  # me only
fi
if [ ! -d "$APP" ]; then
    log "can't find the installed app at $APP (\$3 is $3); skipping"
    exit 0
fi
