#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
# Copyright 2026 Monochrome Icons contributors
"""Standard-library builder preflight tests; fixtures stay in temporary trees."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import build_theme as builder


class BuildTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='monochrome-build-test-')
        self.previous_root=builder.ROOT
        builder.ROOT=Path(self.temp.name)
        self.target=builder.ROOT/'theme'/builder.NAME
        self.path=self.target/'apps/scalable/example.svg'
        self.path.parent.mkdir(parents=True)
        self.path.write_bytes(b'example')
        self.manifest=builder.ROOT/'theme-files.json'
        self.manifest.write_text(json.dumps({'name':builder.NAME,'files':[{
            'file':str(self.path.relative_to(builder.ROOT)),
            'sha256':hashlib.sha256(b'example').hexdigest()}]}))

    def tearDown(self):
        builder.ROOT=self.previous_root
        self.temp.cleanup()

    def test_previous_managed_files_are_eligible(self):
        self.assertEqual(builder.preflight(self.target,self.manifest),{self.path})

    def test_unlisted_user_file_stops_before_writes(self):
        note=self.target/'user-note.txt';note.write_text('keep')
        with self.assertRaises(ValueError):builder.preflight(self.target,self.manifest)
        self.assertEqual(note.read_text(),'keep')
        self.assertEqual(self.path.read_bytes(),b'example')

    def test_edited_managed_file_stops_before_writes(self):
        self.path.write_bytes(b'user edit')
        with self.assertRaises(ValueError):builder.preflight(self.target,self.manifest)
        self.assertEqual(self.path.read_bytes(),b'user edit')

    def test_symlink_stops_before_writes(self):
        (self.target/'linked').symlink_to(self.path)
        with self.assertRaises(ValueError):builder.preflight(self.target,self.manifest)

    def test_native_alias_has_one_cleared_drawing(self):
        asset={'key':'tool','review_status':'cleared'}
        catalog={'native_aliases':[{'name':'native-tool','asset_key':'tool'}]}
        self.assertEqual(builder.icon_names(catalog,[asset])['apps','native-tool'],'tool')
        catalog['native_aliases'][0]['asset_key']='held'
        with self.assertRaises(ValueError):builder.icon_names(catalog,[asset])

    def test_unsafe_or_conflicting_name_is_rejected(self):
        assets=[{'key':'one'},{'key':'two'}]
        for name in ('../escape','..','.','one'):
            catalog={'native_aliases':[{'name':name,'asset_key':'two'}]}
            with self.assertRaises(ValueError):builder.icon_names(catalog,assets)


if __name__=='__main__':unittest.main()
