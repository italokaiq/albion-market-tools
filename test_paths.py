import sys
import unittest
import importlib
import paths


class PathsTest(unittest.TestCase):
    def tearDown(self):
        for attr in ('frozen', '_MEIPASS'):
            if hasattr(sys, attr):
                delattr(sys, attr)
        importlib.reload(paths)

    def test_unfrozen_resource_and_data_share_script_directory(self):
        importlib.reload(paths)
        self.assertEqual(paths.resource_path('items.json').parent, paths._HERE)
        self.assertEqual(paths.data_path('mercado.sqlite3').parent, paths._HERE)
        self.assertEqual(paths.resource_path('x'), paths.data_path('x'))

    def test_frozen_resource_uses_meipass_not_exe_directory(self):
        sys.frozen = True
        sys._MEIPASS = r'C:\Temp\_MEI123456'
        sys.executable = r'C:\Program Files\AlbionMarketTools\AlbionMarketTools.exe'
        importlib.reload(paths)
        self.assertEqual(str(paths.resource_path('items.json')), r'C:\Temp\_MEI123456\items.json')

    def test_frozen_data_uses_exe_directory_not_meipass(self):
        sys.frozen = True
        sys._MEIPASS = r'C:\Temp\_MEI123456'
        sys.executable = r'C:\Program Files\AlbionMarketTools\AlbionMarketTools.exe'
        importlib.reload(paths)
        self.assertEqual(str(paths.data_path('mercado.sqlite3')),
                          r'C:\Program Files\AlbionMarketTools\mercado.sqlite3')

    def test_frozen_resource_and_data_diverge(self):
        sys.frozen = True
        sys._MEIPASS = r'C:\Temp\_MEI123456'
        sys.executable = r'C:\Program Files\AlbionMarketTools\AlbionMarketTools.exe'
        importlib.reload(paths)
        self.assertNotEqual(paths.resource_path('x').parent, paths.data_path('x').parent)
