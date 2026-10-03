import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import update_languages as languages


def repository(repo_id, name, private=False, fork=False, owner='maxsampa'):
    return {'id': repo_id, 'name': name, 'full_name': f'{owner}/{name}',
            'private': private, 'fork': fork, 'owner': {'login': owner}}


class LanguageStatisticsTest(unittest.TestCase):
    def test_includes_private_new_languages_and_all_pages_without_forks_or_duplicates(self):
        pages = [[repository(1, 'public'), repository(2, 'private', private=True),
                  repository(3, 'copy', fork=True), repository(4, 'maxsampa')],
                 [repository(2, 'private', private=True), repository(5, 'new'),
                  repository(6, 'other', owner='someone-else')]]
        responses = {'user': {'login': 'maxsampa'}, 'user/repos': pages,
                     'repos/maxsampa/public/languages': {'Python': 100},
                     'repos/maxsampa/private/languages': {'Kotlin': 300},
                     'repos/maxsampa/new/languages': {'Rust': 100}}
        with patch.object(languages, 'api', side_effect=lambda endpoint, *a, **k: responses[endpoint]) as api:
            totals = languages.aggregate(languages.fetch_languages('maxsampa'))
        self.assertEqual(totals, {'Kotlin': 300, 'Python': 100, 'Rust': 100})
        self.assertEqual(len(api.call_args_list), 5)
        self.assertTrue(api.call_args_list[1].kwargs['paginate'])

    def test_missing_private_access_does_not_write_public_only_card(self):
        responses = {'user': {'login': 'maxsampa'},
                     'user/repos': [[repository(1, 'public')]]}
        with patch.object(languages, 'api', side_effect=lambda endpoint, *a, **k: responses[endpoint]):
            with self.assertRaisesRegex(RuntimeError, 'No private repositories'):
                languages.fetch_languages('maxsampa')

    def test_requires_owner_token(self):
        with patch.object(languages, 'api', return_value={'login': 'someone-else'}):
            with self.assertRaisesRegex(RuntimeError, 'profile owner'):
                languages.fetch_languages('maxsampa')

    def test_api_failure_preserves_existing_snapshot(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'languages.svg'
            path.write_text('previous complete image')
            with patch.object(languages, 'fetch_languages', side_effect=RuntimeError('API failed')):
                with patch('sys.argv', ['update_languages.py', '--output', str(path)]):
                    with self.assertRaises(RuntimeError):
                        languages.main()
            self.assertEqual(path.read_text(), 'previous complete image')

    def test_cli_failure_does_not_expose_private_endpoint_in_error(self):
        result = type('Result', (), {'returncode': 1, 'stdout': '',
                                    'stderr': 'failed: repos/owner/private-name/languages'})()
        with patch.object(languages.subprocess, 'run', return_value=result):
            with self.assertRaises(RuntimeError) as error:
                languages.api('repos/owner/private-name/languages')
        self.assertNotIn('private-name', str(error.exception))

    def test_invalid_or_empty_data_is_rejected(self):
        for data in [[None], [{'Python': -1}], [{'Python': True}], [{'Python': '100'}], [{}]]:
            with self.subTest(data=data), self.assertRaises(ValueError):
                languages.aggregate(data)

    def test_percentage_uses_bytes_and_labels_include_every_language(self):
        totals = languages.aggregate([{'Kotlin': 300, 'Python': 100}, {'Python': 100}])
        svg = languages.render(totals)
        self.assertIn('Kotlin: 60.00%', svg)
        self.assertIn('Python: 40.00%', svg)
        many = {f'Language {i}': 1 for i in range(14)}
        parsed = ET.fromstring(languages.render(many))
        self.assertGreater(int(parsed.attrib['height']), 155)
        texts = [node.text for node in parsed.iter('{http://www.w3.org/2000/svg}text')]
        self.assertTrue(all(name in texts for name in many))

    def test_escapes_labels_and_publishes_only_aggregate_language_data(self):
        svg = languages.render({'C++ & <example>': 42})
        parsed = ET.fromstring(svg)
        self.assertIn('C++ & <example>', [node.text for node in parsed.iter('{http://www.w3.org/2000/svg}text')])
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'languages.svg'
            path.write_text('previous')
            languages.publish(path, svg)
            self.assertEqual(path.read_text(), svg)
            self.assertEqual(list(Path(folder).iterdir()), [path])


if __name__ == '__main__':
    unittest.main()
