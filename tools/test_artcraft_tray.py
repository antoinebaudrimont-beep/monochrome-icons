#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0-only
"""Exact silhouette and malformed-pixmap safety tests; no live bus or desktop."""
import unittest
from unittest.mock import Mock
from artcraft_tray import white_pixels,Tray


class TrayPixels(unittest.TestCase):
    def test_every_alpha_and_original_edge_position_is_preserved(self):
        source=bytes(v for alpha in range(256) for v in (alpha,78,123,251))
        width,height,data=white_pixels([(16,16,source)])[0]
        self.assertEqual((width,height),(16,16))
        self.assertEqual(data[::4],source[::4])
        self.assertEqual(data[:4],b'\0\0\0\0')
        for offset in range(4,len(data),4):self.assertEqual(data[offset+1:offset+4],b'\xff\xff\xff')
        self.assertEqual(source[1:4],bytes([78,123,251]))

    def test_empty_optional_pixmaps_are_retained(self):
        self.assertEqual(white_pixels([]),[])

    def test_invalid_or_unbounded_bitmaps_are_rejected(self):
        for pixmap in [(0,1,b''),(1,1,b'123'),(-1,2,b''),(2048,2048,b'')]:
            with self.assertRaises(ValueError):white_pixels([pixmap])

    def test_discovery_idle_callback_runs_once_not_continuously(self):
        tray=Tray.__new__(Tray)
        tray.tick=Mock(return_value=True)
        self.assertFalse(tray.once())
        tray.tick.assert_called_once_with()


if __name__=='__main__':unittest.main()
