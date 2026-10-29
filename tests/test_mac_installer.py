"""Checks the macOS installer's files (mac_installer/, build_mac_installer.sh) fit together."""
import re
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FOLDER = ROOT / "mac_installer"


class MacInstallerTest(unittest.TestCase):
    def setUp(self):
        self.distribution = ET.parse(FOLDER / "Distribution.xml").getroot()

    def test_choices_match_packages(self):
        outline = [line.get("choice") for line in self.distribution.find("choices-outline")]
        self.assertEqual(outline, ["app", "dock", "desktop"])
        choice_refs = {ref.get("id") for choice in self.distribution.iter("choice") for ref in choice.iter("pkg-ref")}
        files = {ref.get("id"): ref.text for ref in self.distribution.findall("pkg-ref")}
        self.assertEqual(choice_refs, set(files))
        # build_mac_installer.sh makes app.pkg plus one script-only package per optional choice.
        script = (ROOT / "build_mac_installer.sh").read_text(encoding="utf-8")
        self.assertIn('"$work/packages/app.pkg"', script)
        self.assertIn("for choice in dock desktop; do", script)
        self.assertEqual(files, {"com.autoclicker.pkg.app": "app.pkg", "com.autoclicker.pkg.dock": "dock.pkg",
                                 "com.autoclicker.pkg.desktop": "desktop.pkg"})
        self.assertIn("--identifier com.autoclicker.pkg.app ", script)
        self.assertIn('--identifier "com.autoclicker.pkg.$choice"', script)

    def test_app_choice_is_required_and_extras_start_ticked(self):
        choices = {choice.get("id"): choice.attrib for choice in self.distribution.iter("choice")}
        self.assertEqual((choices["app"]["enabled"], choices["app"]["selected"]), ("false", "true"))
        for extra in ("dock", "desktop"):
            self.assertEqual(choices[extra]["start_selected"], "true")

    def test_all_users_me_only_and_other_disks(self):
        domains = self.distribution.find("domains").attrib
        for domain in ("enable_localSystem", "enable_currentUserHome", "enable_anywhere"):
            self.assertEqual(domains[domain], "true")

    def test_version_is_filled_in(self):
        text = (FOLDER / "Distribution.xml").read_text(encoding="utf-8")
        self.assertIn("@VERSION@", text)
        for ref in self.distribution.findall("pkg-ref"):
            self.assertEqual(ref.get("version"), "@VERSION@")
        self.assertTrue(re.search(r"ProductVersion', '\d+\.\d+\.\d+'", (ROOT / "version_info.txt").read_text()))

    def test_scripts_run_under_sh(self):
        for name in ("dock_postinstall", "desktop_postinstall", "common.sh"):
            data = (FOLDER / "scripts" / name).read_bytes()
            self.assertNotIn(b"\r", data, f"{name} must have LF line endings")
        for name in ("dock_postinstall", "desktop_postinstall"):
            data = (FOLDER / "scripts" / name).read_text(encoding="utf-8")
            self.assertTrue(data.startswith("#!/bin/sh\n"))
            self.assertIn('. "$(dirname "$0")/common.sh"', data)
            self.assertTrue(data.rstrip().endswith("exit 0"), f"{name} must never fail the install")

    def test_conclusion_page_exists(self):
        self.assertEqual(self.distribution.find("conclusion").get("file"), "conclusion.html")
        self.assertTrue((FOLDER / "conclusion.html").is_file())


if __name__ == "__main__":
    unittest.main()
