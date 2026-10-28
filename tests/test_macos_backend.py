"""platforms/macos.py against a fake Quartz, so its logic is tested on any OS.

The fake only has the pyobjc names the backend is allowed to use, with their
real values from pyobjc 12, so a misspelled name fails here too. Whether
the real Quartz calls behave as expected is only checked on a Mac.
"""
import importlib
import os
import sys
import time
import types
import unittest
from unittest import mock


class FakeQuartz(types.ModuleType):
    CONSTANTS = dict(
        kCGHIDEventTap=0, kCGMouseEventClickState=1, kCGMouseEventButtonNumber=3,
        kCGEventLeftMouseDown=1, kCGEventLeftMouseUp=2, kCGEventRightMouseDown=3, kCGEventRightMouseUp=4,
        kCGEventMouseMoved=5, kCGEventOtherMouseDown=25, kCGEventOtherMouseUp=26,
        kCGMouseButtonLeft=0, kCGMouseButtonRight=1, kCGMouseButtonCenter=2,
        kCGSessionEventTap=1, kCGHeadInsertEventTap=0, kCGEventTapOptionDefault=0, kCGEventTapOptionListenOnly=1,
        kCGEventKeyDown=10, kCGEventKeyUp=11, kCGKeyboardEventKeycode=9,
        kCGEventTapDisabledByTimeout=0xFFFFFFFE, kCGEventTapDisabledByUserInput=0xFFFFFFFF,
        kCGWindowListOptionOnScreenOnly=1, kCGWindowListExcludeDesktopElements=16, kCGNullWindowID=0,
        kCFRunLoopDefaultMode="kCFRunLoopDefaultMode",
    )

    def __init__(self):
        super().__init__("Quartz")
        for name, value in self.CONSTANTS.items():
            setattr(self, name, value)
        self.cursor = (0.0, 0.0)
        self.posted = []
        self.taps = []
        self.deny_taps = 0
        self.listen_ok = True
        self.requests = []
        self.windows = []

    # Mouse events
    def CGEventCreate(self, source):
        return {"location": self.cursor, "fields": {}}

    def CGEventGetLocation(self, event):
        return event["location"]

    def CGEventCreateMouseEvent(self, source, event_type, location, button):
        return {"type": event_type, "location": location, "button": button, "fields": {}}

    def CGEventSetIntegerValueField(self, event, field, value):
        event["fields"][field] = value

    def CGEventGetIntegerValueField(self, event, field):
        return event["fields"].get(field, 0)

    def CGEventGetFlags(self, event):
        return event.get("flags", 0)

    def CGEventPost(self, tap, event):
        assert tap == self.kCGHIDEventTap
        self.posted.append(event)
        self.cursor = event["location"]  # posted mouse events move the cursor

    # Event taps and run loops
    def CGEventMaskBit(self, event_type):
        return 1 << event_type

    def CGEventTapCreate(self, where, place, options, mask, callback, refcon):
        if self.deny_taps:
            self.deny_taps -= 1
            return None
        tap = {"options": options, "mask": mask, "callback": callback, "enabled": False}
        self.taps.append(tap)
        return tap

    def CGEventTapEnable(self, tap, enabled):
        tap["enabled"] = enabled

    def CFMachPortCreateRunLoopSource(self, allocator, tap, order):
        return ("source", id(tap))

    def CFRunLoopGetCurrent(self):
        return "loop"

    def CFRunLoopAddSource(self, loop, source, mode):
        pass

    def CFRunLoopRunInMode(self, mode, seconds, return_after_source):
        time.sleep(min(seconds, 0.005))

    def CFRunLoopStop(self, loop):
        pass

    # Screens, windows, permissions
    def CGGetDisplaysWithPoint(self, point, max_displays, displays, count):
        x, y = point
        return (0, (1,), 1) if 0 <= x < 1920 and 0 <= y < 1080 else (0, (), 0)

    def CGWindowListCopyWindowInfo(self, options, window_id):
        return self.windows

    def CGRectMakeWithDictionaryRepresentation(self, bounds, out):
        return (True, bounds) if bounds else (False, None)

    def CGRectContainsPoint(self, rect, point):
        return (rect["X"] <= point[0] < rect["X"] + rect["Width"]
                and rect["Y"] <= point[1] < rect["Y"] + rect["Height"])

    def CGPreflightListenEventAccess(self):
        return self.listen_ok

    def CGRequestListenEventAccess(self):
        self.requests.append("listen")


class FakeHIServices(types.ModuleType):
    kAXTrustedCheckOptionPrompt = "AXTrustedCheckOptionPrompt"

    def __init__(self):
        super().__init__("HIServices")
        self.trusted = True
        self.prompts = []

    def AXIsProcessTrusted(self):
        return self.trusted

    def AXIsProcessTrustedWithOptions(self, options):
        self.prompts.append(options)
        return self.trusted


def wait_until(condition, timeout=1.0):
    deadline = time.perf_counter() + timeout
    while not condition() and time.perf_counter() < deadline:
        time.sleep(0.005)
    return condition()


class MacBackendTest(unittest.TestCase):
    def setUp(self):
        import platforms
        self.q = FakeQuartz()
        self.hi = FakeHIServices()
        real = vars(platforms).get("macos")  # the real backend, on a Mac
        with mock.patch.dict(sys.modules, {"Quartz": self.q, "HIServices": self.hi}):
            sys.modules.pop("platforms.macos", None)
            self.mac = importlib.import_module("platforms.macos")
        if real is None:
            del platforms.macos  # importing set it on the package
        else:
            platforms.macos = real
        self.mac._EventTap.RETRY_SECONDS = 0.01
        self.started = []

    def tearDown(self):
        for thing in self.started:
            thing.stop()

    def start(self, thing):
        thing.start()
        self.started.append(thing)
        self.assertTrue(wait_until(lambda: self.q.taps and self.q.taps[-1]["enabled"]), "tap never enabled")
        return self.q.taps[-1]

    def summary(self):
        return [(e["type"], e["location"], e["button"], e["fields"].get(self.q.kCGMouseEventClickState))
                for e in self.q.posted]

    def test_defines_everything_the_platforms_package_imports(self):
        import platforms
        names = [n for n in vars(platforms) if not n.startswith("_") and n != "sys"
                 and not isinstance(getattr(platforms, n), types.ModuleType)]
        self.assertGreater(len(names), 15)
        self.assertEqual([n for n in names if not hasattr(self.mac, n)], [])

    # Mouse output
    def test_click_at_moves_clicks_and_moves_back(self):
        self.q.cursor = (10.0, 20.0)
        self.mac.Mouse().click_at(300, 400, "right", 2)
        q = self.q
        self.assertEqual(self.summary(), [
            (q.kCGEventMouseMoved, (300, 400), q.kCGMouseButtonLeft, None),
            (q.kCGEventRightMouseDown, (300, 400), q.kCGMouseButtonRight, 1),
            (q.kCGEventRightMouseUp, (300, 400), q.kCGMouseButtonRight, 1),
            (q.kCGEventRightMouseDown, (300, 400), q.kCGMouseButtonRight, 2),
            (q.kCGEventRightMouseUp, (300, 400), q.kCGMouseButtonRight, 2),
            (q.kCGEventMouseMoved, (10, 20), q.kCGMouseButtonLeft, None),
        ])

    def test_click_at_the_cursor(self):
        self.q.cursor = (5.4, 6.6)
        self.mac.Mouse().click("middle")
        q = self.q
        self.assertEqual(self.summary(), [(q.kCGEventOtherMouseDown, (5, 7), q.kCGMouseButtonCenter, 1),
                                          (q.kCGEventOtherMouseUp, (5, 7), q.kCGMouseButtonCenter, 1)])

    def test_position_is_rounded(self):
        self.q.cursor = (10.6, 20.4)
        self.assertEqual(self.mac.Mouse().position, (11, 20))

    # Screens and windows
    def test_on_screen(self):
        self.assertTrue(self.mac.on_screen(0, 0))
        self.assertFalse(self.mac.on_screen(-5, 0))

    def test_is_own_window_looks_at_the_frontmost_visible_window(self):
        everywhere = {"X": 0, "Y": 0, "Width": 1920, "Height": 1080}
        self.q.windows = [
            {"kCGWindowAlpha": 0, "kCGWindowOwnerPID": 1, "kCGWindowBounds": everywhere},  # invisible overlay
            {"kCGWindowAlpha": 1, "kCGWindowOwnerPID": os.getpid(),
             "kCGWindowBounds": {"X": 0, "Y": 0, "Width": 100, "Height": 100}},
            {"kCGWindowAlpha": 1, "kCGWindowOwnerPID": 1, "kCGWindowBounds": everywhere},
        ]
        self.assertTrue(self.mac.is_own_window(50, 50))
        self.assertFalse(self.mac.is_own_window(500, 500))
        self.q.windows = []
        self.assertFalse(self.mac.is_own_window(50, 50))

    # Event taps
    def test_key_source_reports_names_and_modifiers(self):
        pressed, released = [], []
        tap = self.start(self.mac.KeySource(lambda n, m: pressed.append((n, m)), released.append))
        q = self.q
        self.assertEqual(tap["options"], q.kCGEventTapOptionListenOnly)
        self.assertEqual(tap["mask"], (1 << q.kCGEventKeyDown) | (1 << q.kCGEventKeyUp))
        down = {"fields": {q.kCGKeyboardEventKeycode: 0x61}, "flags": 0x100000 | 0x20000}
        self.assertIs(tap["callback"](None, q.kCGEventKeyDown, down, None), down)
        tap["callback"](None, q.kCGEventKeyUp, {"fields": {q.kCGKeyboardEventKeycode: 0x61}}, None)
        self.assertEqual(pressed, [("f6", {"win", "shift"})])
        self.assertEqual(released, ["f6"])

    def test_tap_retries_until_permission_is_granted(self):
        self.q.deny_taps = 3
        self.start(self.mac.KeySource(lambda n, m: None, lambda n: None))
        self.assertEqual(len(self.q.taps), 1)

    def test_tap_turned_off_by_macos_is_turned_back_on(self):
        tap = self.start(self.mac.KeySource(lambda n, m: None, lambda n: None))
        tap["enabled"] = False
        tap["callback"](None, self.q.kCGEventTapDisabledByTimeout, None, None)
        self.assertTrue(tap["enabled"])

    def test_a_failing_handler_never_swallows_input(self):
        def broken(name, modifiers):
            raise RuntimeError("bug")
        tap = self.start(self.mac.KeySource(broken, lambda n: None))
        event = {"fields": {self.q.kCGKeyboardEventKeycode: 0}}
        self.assertIs(tap["callback"](None, self.q.kCGEventKeyDown, event, None), event)

    def test_stop_ends_the_tap_thread(self):
        source = self.mac.KeySource(lambda n, m: None, lambda n: None)
        tap = self.start(source)
        source.stop()
        self.assertTrue(wait_until(lambda: not tap["enabled"]))

    def test_picker_swallows_one_click_and_stops(self):
        picked = []
        picker = self.mac.PointPicker(lambda x, y: picked.append((x, y)))
        tap = self.start(picker)
        q = self.q
        self.assertEqual(tap["options"], q.kCGEventTapOptionDefault)  # needed to swallow
        self.assertIsNone(tap["callback"](None, q.kCGEventLeftMouseDown, {"location": (100.4, 200.6)}, None))
        self.assertEqual(picked, [(100, 201)])
        self.assertIsNone(tap["callback"](None, q.kCGEventLeftMouseUp, {"location": (100.4, 200.6)}, None))
        self.assertTrue(wait_until(lambda: not tap["enabled"]), "picker didn't stop after the click")

    def test_mouse_listener_reports_buttons_and_ignores_side_buttons(self):
        presses = []
        tap = self.start(self.mac.MouseListener(lambda x, y, b: presses.append((x, y, b))))
        q = self.q
        self.assertEqual(tap["options"], q.kCGEventTapOptionListenOnly)
        for event_type, number in ((q.kCGEventRightMouseDown, 1), (q.kCGEventOtherMouseDown, 3),
                                   (q.kCGEventOtherMouseDown, 2)):
            event = {"location": (7.0, 8.0), "fields": {q.kCGMouseEventButtonNumber: number}}
            self.assertIs(tap["callback"](None, event_type, event, None), event)
        self.assertEqual(presses, [(7, 8, "right"), (7, 8, "middle")])

    # Permissions
    def test_permission_problem(self):
        self.assertIsNone(self.mac.permission_problem())
        self.hi.trusted = False
        self.assertIn("Accessibility", self.mac.permission_problem())
        self.q.listen_ok = False
        self.assertTrue(self.mac.permission_problem().endswith("Accessibility and Input Monitoring"))

    def test_request_permissions_prompts_only_for_what_is_missing(self):
        self.mac.request_permissions()
        self.assertEqual((self.hi.prompts, self.q.requests), ([], []))
        self.hi.trusted, self.q.listen_ok = False, False
        self.mac.request_permissions()
        self.assertEqual(self.hi.prompts, [{"AXTrustedCheckOptionPrompt": True}])
        self.assertEqual(self.q.requests, ["listen"])

    # Files, look, sounds
    def test_settings_folder(self):
        self.assertEqual(self.mac.settings_folder().parts[-3:], ("Library", "Application Support", "AutoClicker"))

    def test_system_uses_dark(self):
        def run(stdout="", error=None):
            if error:
                return mock.patch.object(self.mac.subprocess, "run", side_effect=error)
            return mock.patch.object(self.mac.subprocess, "run", return_value=mock.Mock(stdout=stdout))
        with run("Dark\n"):
            self.assertTrue(self.mac.system_uses_dark())
        with run(""):  # light mode: the setting doesn't exist
            self.assertFalse(self.mac.system_uses_dark())
        with run(error=OSError()):
            self.assertFalse(self.mac.system_uses_dark())

    def test_play_sound(self):
        with mock.patch.object(self.mac.subprocess, "Popen") as popen:
            self.mac.play_sound(True)
            self.mac.play_sound(False)
        self.assertEqual([c.args[0] for c in popen.call_args_list],
                         [["afplay", self.mac.SOUNDS[True]], ["afplay", self.mac.SOUNDS[False]]])
        with mock.patch.object(self.mac.subprocess, "Popen", side_effect=OSError()):
            self.mac.play_sound(True)  # must not raise

    def test_set_window_dark(self):
        window = mock.Mock()
        self.mac.set_window_dark(window, True)
        window.tk.call.assert_called_once_with("::tk::unsupported::MacWindowStyle", "appearance", window, "darkaqua")
        window.tk.call.side_effect = self.mac.tk.TclError("old Tk")
        self.mac.set_window_dark(window, False)  # must not raise


if __name__ == "__main__":
    unittest.main()
