import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
import app_update as au


class ParseVersionTest(unittest.TestCase):
    def test_parses_plain_and_v_prefixed(self):
        self.assertEqual(au.parse_version('1.2.3'), (1, 2, 3))
        self.assertEqual(au.parse_version('v1.2.3'), (1, 2, 3))
        self.assertEqual(au.parse_version('V2.0.10'), (2, 0, 10))

    def test_rejects_unexpected_formats(self):
        for bad in ('1.2', '1.2.3.4', 'abc', '', '1.2.x'):
            with self.assertRaises(ValueError):
                au.parse_version(bad)


class CheckForUpdateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.patcher = patch('app_update.resource_path', lambda name: self.dir / name)
        self.patcher.start()

    def tearDown(self):
        self.patcher.stop()
        self.tmp.cleanup()

    def write_version(self, text):
        (self.dir / 'VERSION').write_text(text, encoding='utf-8')

    def test_newer_remote_reports_update_available(self):
        self.write_version('1.0.0\n')
        report = au.check_for_update(fetcher=lambda: {'tag_name': 'v1.1.0', 'html_url': 'https://x/releases/v1.1.0'})
        self.assertTrue(report['ok'])
        self.assertTrue(report['update_available'])
        self.assertEqual(report['url'], 'https://x/releases/v1.1.0')

    def test_same_or_older_remote_reports_no_update(self):
        self.write_version('1.1.0')
        for tag in ('1.1.0', '1.0.0', 'v1.1.0'):
            report = au.check_for_update(fetcher=lambda tag=tag: {'tag_name': tag, 'html_url': 'x'})
            self.assertTrue(report['ok'])
            self.assertFalse(report['update_available'])

    def test_missing_local_version_file_still_reports_remote(self):
        report = au.check_for_update(fetcher=lambda: {'tag_name': 'v1.0.0', 'html_url': 'x'})
        self.assertTrue(report['ok'])
        self.assertIsNone(report['local_version'])
        self.assertTrue(report['update_available'])  # sem versão local, não presume estar em dia

    def test_network_failure_does_not_raise(self):
        def failing():
            raise OSError('sem rede')
        report = au.check_for_update(fetcher=failing)
        self.assertFalse(report['ok'])
        self.assertIn('sem rede', report['error'])

    def test_malformed_remote_tag_reported_without_raising(self):
        self.write_version('1.0.0')
        report = au.check_for_update(fetcher=lambda: {'tag_name': 'not-a-version', 'html_url': 'x'})
        self.assertFalse(report['ok'])

    def test_never_touches_real_network(self):
        with patch('app_update.urllib.request.urlopen', side_effect=AssertionError('rede real chamada')):
            au.check_for_update(fetcher=lambda: {'tag_name': 'v1.0.0', 'html_url': 'x'})


if __name__ == '__main__':
    unittest.main()
