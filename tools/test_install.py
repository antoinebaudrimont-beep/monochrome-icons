#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Installer tests only use temporary homes; no real desktop settings are changed."""
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
INSTALL=ROOT/'tools/install_theme.py'
spec=importlib.util.spec_from_file_location('install_theme',INSTALL)
installer=importlib.util.module_from_spec(spec);spec.loader.exec_module(installer)
FIXTURE=b'''[Desktop Entry]\nName=Mail\nType=Application\nExec=mail-program --url %u\nIcon=original\nIcon[de]=original-localized\nTerminal=true\n\n[Desktop Action Compose]\nExec=mail-program --compose\nIcon=compose\n'''


class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='monochrome-install-test-')
        self.home=Path(self.temp.name)/'test-user'
        self.home.mkdir()

    def tearDown(self):self.temp.cleanup()

    def run_install(self,*options,expected=0):
        result=subprocess.run([sys.executable,str(INSTALL),'install','--home',str(self.home),*options],capture_output=True,text=True)
        self.assertEqual(result.returncode,expected,result.stderr+result.stdout)
        return result

    def manifest(self):
        return next((self.home/'.local/state/monochrome-icons/backups').glob('*/manifest.json'))

    def restore(self,*options,expected=0):
        result=subprocess.run([sys.executable,str(INSTALL),'restore',str(self.manifest()),'--home',str(self.home),*options],capture_output=True,text=True)
        self.assertEqual(result.returncode,expected,result.stderr+result.stdout)
        return result

    @unittest.skipUnless(json.loads((ROOT/'assets.json').read_text())['release_status']!='ready','Released catalogs do not require draft opt-in')
    def test_draft_requires_explicit_opt_in(self):
        self.run_install(expected=1)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_dry_run_is_read_only(self):
        self.run_install('--allow-draft','--dry-run','--weather')
        self.assertEqual(list(self.home.iterdir()),[])

    def test_known_apps_mapping_preserves_commands(self):
        app=self.home/'.local/share/applications/aerc.desktop'
        app.parent.mkdir(parents=True);app.write_bytes(FIXTURE)
        self.run_install('--allow-draft','--known-apps','--menu')
        if any('aerc.desktop' in a.get('desktop_ids',[]) for a in json.loads((ROOT/'assets.json').read_text())['assets']):
            self.assertEqual(app.read_bytes(),installer.icon_only(FIXTURE,'monochrome-aerc'))
        self.restore()
        self.assertEqual(app.read_bytes(),FIXTURE)

    def test_install_restore_preserves_launcher_and_user_files(self):
        app=self.home/'.local/share/applications/aerc.desktop'
        app.parent.mkdir(parents=True);app.write_bytes(FIXTURE);app.chmod(0o755)
        self.run_install('--allow-draft','--weather','--map','aerc.desktop=aerc')
        changed=app.read_bytes()
        self.assertEqual(changed,FIXTURE.replace(b'Icon=original',b'Icon=monochrome-aerc').replace(b'Icon[de]=original-localized',b'Icon[de]=monochrome-aerc'))
        self.assertEqual(app.stat().st_mode&0o777,0o755)
        package=json.loads((ROOT/'theme-files.json').read_text())
        theme=self.home/'.local/share/icons'/package['name']
        self.assertEqual(len(list(theme.rglob('*.png'))),len(package['files'])-1)
        self.assertEqual(len(list(theme.rglob('*.svg'))),0)
        for name,key in [('mx-tools','mx-tools'),('mx-viewer','mx-viewer'),('utilities-terminal','xfce4-terminal')]:
            entry=next(e for e in package['files'] if e['file']==f'theme/MonochromeIcons/apps/48/{name}.png')
            self.assertEqual(entry['asset_key'],key)
            self.assertEqual(hashlib.sha256((theme/'apps/48'/f'{name}.png').read_bytes()).hexdigest(),entry['sha256'])
        self.assertEqual(len(list((self.home/'.config/xfce4/weather/icons/monochrome').rglob('*.png'))),114)
        # Additional files must survive restore; empty directories alone are removed.
        extra=theme/'user-note.txt';extra.write_text('Keep me')
        self.restore('--dry-run')
        self.assertEqual(app.read_bytes(),changed)
        self.restore()
        self.assertEqual(app.read_bytes(),FIXTURE)
        self.assertEqual(extra.read_text(),'Keep me')
        self.assertFalse((theme/'index.theme').exists())
        self.assertTrue((self.manifest().parent/'files').exists())

    def test_conflict_blocks_all_restore_writes(self):
        self.run_install('--allow-draft')
        manifest=json.loads(self.manifest().read_text())
        first=Path(manifest['files'][0]['target']);last=Path(manifest['files'][-1]['target'])
        first.write_bytes(first.read_bytes()+b'<!-- user edit -->')
        before=last.read_bytes()
        self.restore(expected=1)
        self.assertEqual(last.read_bytes(),before)
        self.assertIn(b'user edit',first.read_bytes())

    def test_refuses_overwrite_and_unsafe_mapping(self):
        self.run_install('--allow-draft','--map','../unsafe.desktop=aerc',expected=1)
        self.assertEqual(list(self.home.iterdir()),[])
        self.run_install('--allow-draft')
        self.run_install('--allow-draft',expected=1)

    def test_isolated_home_cannot_activate_host_theme(self):
        self.run_install('--allow-draft','--activate',expected=1)
        self.assertEqual(list(self.home.iterdir()),[])

    def test_icon_field_insertion_and_action_preservation(self):
        original=b'[Desktop Entry]\r\nExec=browser %u\r\n[Desktop Action Open]\r\nIcon=action\r\n'
        result=installer.icon_only(original,'monochrome-chawan')
        self.assertEqual(result,b'[Desktop Entry]\r\nExec=browser %u\r\nIcon=monochrome-chawan\r\n[Desktop Action Open]\r\nIcon=action\r\n')


if __name__=='__main__':unittest.main()
