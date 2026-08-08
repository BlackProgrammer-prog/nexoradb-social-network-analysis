from __future__ import annotations

import unittest

from backend.file_parser import FileFormatError, parse_relationship_file


class FileParserTests(unittest.TestCase):
    def test_parses_and_deduplicates_reverse_pairs(self) -> None:
        parsed = parse_relationship_file(b"U01 U02 1\nU02\tU01\t1\nU02 U03 1\n")
        self.assertEqual(parsed.lines_read, 3)
        self.assertEqual(parsed.users, ("U01", "U02", "U03"))
        self.assertEqual(len(parsed.pairs), 2)
        self.assertEqual(parsed.duplicates_skipped, 1)

    def test_rejects_invalid_rows_before_import(self) -> None:
        with self.assertRaises(FileFormatError) as context:
            parse_relationship_file(b"U01 U01 1\nU01 U02 0\nbroken\n")
        self.assertEqual(len(context.exception.errors), 3)

    def test_rejects_empty_file(self) -> None:
        with self.assertRaises(FileFormatError):
            parse_relationship_file(b"\n\t\n")


if __name__ == "__main__":
    unittest.main()

