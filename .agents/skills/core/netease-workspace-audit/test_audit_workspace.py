"""Regression for false print audit positives; no project writes."""
import unittest
import tempfile
from pathlib import Path
import zipfile
import audit_workspace as audit
from audit_workspace import print_baseline_findings

class PrintAuditTests(unittest.TestCase):
    def test_formatted_log_single_argument(self):
        self.assertEqual(print_baseline_findings('print("a=%s b=%s" % (a, b))'), [])

    def test_nested_tuple_and_literal_commas(self):
        self.assertEqual(print_baseline_findings('print("a,b(end=)" % ((a, b),))'), [])

    def test_comment_and_string_are_not_calls(self):
        self.assertEqual(print_baseline_findings('# print(a, b)\nx = "print(a, end=1)"'), [])

    def test_real_multiple_arguments_are_flagged(self):
        self.assertEqual(print_baseline_findings('print(a, b)'), [("print_multi", 1)])

    def test_multiline_multiple_arguments_are_flagged(self):
        self.assertEqual(print_baseline_findings('print(\n a,\n b\n)'), [("print_multi", 1)])

    def test_keywords_are_flagged(self):
        self.assertEqual(print_baseline_findings('print(a, end="")'), [("print_kw", 1), ("print_multi", 1)])

    def test_python2_bare_print_is_not_a_parse_failure(self):
        self.assertEqual(print_baseline_findings("print 'legacy'\nprint((a, b))"), [])
        self.assertEqual(print_baseline_findings("if ok:\n    print(a)\n  print(b)"), [("tokenize_error", 3)])

class ArchiveAuditTests(unittest.TestCase):
    def check_archive(self, name, entries):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            project = root / 'mcstudio_project' / 'Example_v1.0'
            project.mkdir(parents=True)
            with zipfile.ZipFile(project / name, 'w') as archive:
                for entry in entries:
                    archive.writestr(entry, '{}')
            previous = audit.RESULTS[:]
            audit.RESULTS.clear()
            try:
                audit.check_archives(str(root))
                return audit.RESULTS[:]
            finally:
                audit.RESULTS[:] = previous

    def test_editable_developer_project_is_not_submission(self):
        results = self.check_archive('Example_DeveloperProject.zip',
            ['behavior_packs/BP/manifest.json', 'resource_packs/RP/manifest.json', 'README.md'])
        self.assertFalse(any(r[0] == 'FAIL' for r in results))

    def test_submission_must_have_direct_manifests(self):
        results = self.check_archive('Example_Addon.zip',
            ['behavior_packs/BP/manifest.json', 'resource_packs/RP/manifest.json'])
        self.assertTrue(any('must not wrap' in r[2] for r in results))

    def test_mcstudio_must_have_wrappers(self):
        results = self.check_archive('Example_MCStudio.zip', ['BP/manifest.json', 'RP/manifest.json'])
        self.assertTrue(any(r[0] == 'FAIL' for r in results))

    def test_named_legacy_submission_is_supported(self):
        results = self.check_archive('Example_Developer_Submission.zip', ['BP/manifest.json', 'RP/manifest.json'])
        self.assertFalse(any(r[0] == 'FAIL' for r in results))

    def test_unknown_archive_is_not_assumed_to_be_submission(self):
        results = self.check_archive('Example_source.zip', ['README.md'])
        self.assertTrue(any(r[0] == 'WARNING' for r in results))
        self.assertFalse(any(r[0] == 'FAIL' for r in results))

    def test_developer_archive_still_rejects_cache(self):
        results = self.check_archive('Example_DeveloperProject.zip',
            ['behavior_packs/BP/manifest.json', 'resource_packs/RP/manifest.json', '__pycache__/x.pyc'])
        self.assertTrue(any('cache/temp' in r[2] for r in results))

if __name__ == '__main__':
    unittest.main()
