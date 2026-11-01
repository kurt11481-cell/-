import importlib.util
import os
import tempfile
import unittest

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
MAKE_INDEX = os.path.join(REPO, 'docs', 'claude', 'make-index.py')


def load_module():
    spec = importlib.util.spec_from_file_location('make_index_under_test', MAKE_INDEX)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def touch(path, text=''):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', encoding='utf-8', newline='\n') as f:
        f.write(text)


class MakeIndexLinksTest(unittest.TestCase):
    def setUp(self):
        self.mod = load_module()
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = self.tmp.name
        self.mod.DOCS = self.root

    def build(self):
        return self.mod.docs_index()

    def test_plain_names_become_links_and_keep_note(self):
        touch(os.path.join(self.root, 'a-2026-11-01.md'), '---\nid: a-doc\nstatus: done\n---\n# A\n')
        touch(os.path.join(self.root, 'b.md'), '# B only\n')
        out = self.build()
        self.assertIn('| [a-2026-11-01.md](a-2026-11-01.md) |', out)
        self.assertIn('| [b.md](b.md) |', out)
        b_row = [ln for ln in out.split('\n') if ln.startswith('| [b.md]')][0]
        self.assertTrue(b_row.endswith('| 머리말 없음 |'))
        a_row = [ln for ln in out.split('\n') if ln.startswith('| [a-2026-11-01.md]')][0]
        self.assertIn('| 2026-11-01 | a-doc | done |', a_row)

    def test_space_and_paren_names_use_angle_brackets(self):
        touch(os.path.join(self.root, 'c d.md'), '# C\n')
        touch(os.path.join(self.root, 'e(1).md'), '# E\n')
        out = self.build()
        self.assertIn('| [c d.md](<c d.md>) |', out)
        self.assertIn('| [e(1).md](<e(1).md>) |', out)

    def test_subfolder_links(self):
        touch(os.path.join(self.root, 'lib', 'README.md'))
        touch(os.path.join(self.root, 'lib', 'INDEX.md'))
        touch(os.path.join(self.root, 'x', 'INDEX.md'))
        touch(os.path.join(self.root, 'y', 'note.txt'))
        out = self.build()
        self.assertIn('| [lib/](lib/README.md) | 2 |', out)
        self.assertIn('| [x/](x/INDEX.md) | 1 |', out)
        self.assertIn('| y/ | 1 |', out)
        self.assertNotIn('[y/]', out)

    def test_subfolder_name_with_space_uses_angle_brackets(self):
        touch(os.path.join(self.root, 'my dir', 'README.md'))
        out = self.build()
        self.assertIn('| [my dir/](<my dir/README.md>) | 1 |', out)

    def test_dot_folders_and_index_files_excluded(self):
        touch(os.path.join(self.root, '.obsidian', 'app.json'), '{}')
        touch(os.path.join(self.root, 'INDEX-auto.md'), '# old\n')
        touch(os.path.join(self.root, 'INDEX-outputs-auto.md'), '# old\n')
        touch(os.path.join(self.root, 'real.md'), '# real\n')
        out = self.build()
        self.assertNotIn('.obsidian', out)
        self.assertNotIn('INDEX-auto.md', out)
        self.assertNotIn('INDEX-outputs-auto.md', out)
        self.assertIn('| [real.md](real.md) |', out)

    def test_other_files_table_unchanged(self):
        touch(os.path.join(self.root, 'data.json'), '{}')
        out = self.build()
        self.assertIn('## 기타 파일', out)
        row = [ln for ln in out.split('\n') if ln.startswith('| data.json ')][0]
        self.assertNotIn('[', row)

    def test_deterministic_and_header(self):
        touch(os.path.join(self.root, 'a.md'), '# A\n')
        touch(os.path.join(self.root, 'lib', 'README.md'))
        first = self.build()
        second = self.build()
        self.assertEqual(first, second)
        lines = first.split('\n')
        self.assertEqual(lines[0], '---')
        self.assertEqual(lines[1], 'id: index-auto-docs')
        self.assertEqual(lines[2], 'type: index')
        self.assertEqual(lines[3], 'status: generated')
        self.assertTrue(lines[4].startswith('summary: '))
        self.assertEqual(lines[5], '---')
        self.assertIn('- Obsidian 그래프: 이 목록의 링크로 모든 문서가 이어진다(문서끼리 직접 잇는 선은 아님).', lines)


if __name__ == '__main__':
    unittest.main()
