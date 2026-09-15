import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from history import History


class HistoryTest(unittest.TestCase):
    def setUp(self):
        self.tmp = TemporaryDirectory()
        self.h = History(Path(self.tmp.name) / 'historico.json')

    def tearDown(self):
        self.tmp.cleanup()

    def test_empty_history_without_file(self):
        self.assertEqual(self.h.read(), {'version': 1, 'entries': []})

    def test_add_prepends_newest_first_and_sets_metadata(self):
        first = self.h.add(dict(kind='flipping', item='T4_BAG'))
        second = self.h.add(dict(kind='craft', product='T4_MAIN_SWORD'))
        entries = self.h.read()['entries']
        self.assertEqual([e['id'] for e in entries], [second, first])
        self.assertIsNone(entries[0]['realized'])
        self.assertIn('recorded_at', entries[0])

    def test_confirm_sets_realized_without_touching_predicted(self):
        entry_id = self.h.add(dict(kind='flipping', item='T4_BAG', predicted=dict(net=100)))
        self.h.confirm(entry_id, dict(net=80))
        entry = self.h.read()['entries'][0]
        self.assertEqual(entry['realized']['net'], 80)
        self.assertIn('confirmed_at', entry['realized'])
        self.assertEqual(entry['predicted']['net'], 100)

    def test_confirm_unknown_id_raises_and_keeps_file(self):
        self.h.add(dict(kind='flipping'))
        with self.assertRaises(KeyError):
            self.h.confirm('missing', dict(net=1))
        self.assertEqual(len(self.h.read()['entries']), 1)

    def test_delete_removes_only_matching_entry(self):
        keep = self.h.add(dict(kind='flipping', item='A'))
        remove = self.h.add(dict(kind='flipping', item='B'))
        self.h.delete(remove)
        entries = self.h.read()['entries']
        self.assertEqual([e['id'] for e in entries], [keep])

    def test_delete_unknown_id_raises(self):
        with self.assertRaises(KeyError):
            self.h.delete('missing')

    def test_malformed_file_rejected_without_overwrite(self):
        self.h.path.write_text('{"not":"valid"}', encoding='utf-8')
        with self.assertRaises(ValueError):
            self.h.read()
        self.assertEqual(json.loads(self.h.path.read_text(encoding='utf-8')), {'not': 'valid'})

    def test_backup_created_on_second_write(self):
        self.h.add(dict(kind='flipping'))
        self.h.add(dict(kind='craft'))
        self.assertTrue(self.h.path.with_suffix('.json.bak').exists())
