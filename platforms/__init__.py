"""Operating-system layer: everything that differs between Windows and macOS.

windows.py and macos.py define the same names; the rest of the app imports
them from here and stays OS-independent.
"""
import sys

if sys.platform == "darwin":
    from platforms.macos import (
        EXAMPLE_COMBO, KEY_NAMES, MODIFIER_LABELS, NATIVE_DARK, NATIVE_THEME, OS_NAME, TYPING_MODIFIERS,
        KeySource, Mouse, MouseListener, PointPicker, is_own_window, on_screen, permission_problem,
        play_sound, prepare_process, request_permissions, set_app_icon, set_window_dark, settings_folder,
        system_uses_dark,
    )
else:
    from platforms.windows import (
        EXAMPLE_COMBO, KEY_NAMES, MODIFIER_LABELS, NATIVE_DARK, NATIVE_THEME, OS_NAME, TYPING_MODIFIERS,
        KeySource, Mouse, MouseListener, PointPicker, is_own_window, on_screen, permission_problem,
        play_sound, prepare_process, request_permissions, set_app_icon, set_window_dark, settings_folder,
        system_uses_dark,
    )
