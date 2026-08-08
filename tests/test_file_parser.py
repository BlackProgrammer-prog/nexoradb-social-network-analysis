"""Unit tests for the file import parser."""

import pytest
from backend.import_service import parse_line, validate_file, process_import


class TestFileParser:
    """Test suite for file parsing and validation."""

    def test_parse_valid_line(self):
        """Test parsing a valid three-column line."""
        assert parse_line("U01 U02 1") == ("U01", "U02")

    def test_parse_with_tabs(self):
        """Test parsing with tab separators."""
        assert parse_line("U01\tU02\t1") == ("U01", "U02")

    def test_parse_with_multiple_spaces(self):
        """Test parsing with multiple spaces."""
        assert parse_line("U01    U02    1") == ("U01", "U02")

    def test_parse_self_loop_rejected(self):
        """Test self-loop rejection."""
        assert parse_line("U01 U01 1") is None

    def test_parse_invalid_flag(self):
        """Test invalid flag values."""
        assert parse_line("U01 U02 0") is None
        assert parse_line("U01 U02 2") is None
        assert parse_line("U01 U02 yes") is None

    def test_parse_reverse_order_normalized(self):
        """Test reverse order normalization."""
        assert parse_line("U02 U01 1") == ("U01", "U02")

    def test_parse_empty_line(self):
        """Test empty line handling."""
        assert parse_line("") is None
        assert parse_line("   ") is None

    def test_validate_file_valid(self):
        """Test validation of a valid file."""
        content = "U01 U02 1\nU03 U04 1\nU01 U02 1\n"
        errors = validate_file(content)
        assert len(errors) == 0

    def test_validate_file_with_errors(self):
        """Test validation with error lines."""
        content = "U01 U02 1\nU01 U01 1\nU02 U03 0\n"
        errors = validate_file(content)
        assert len(errors) == 2

    def test_process_import_statistics(self):
        """Test import statistics calculation."""
        content = "U01 U02 1\nU03 U04 1\n"
        result = process_import(content)
        assert result.unique_users == 4
        assert result.unique_pairs == 2
        assert result.directed_edges_created == 4
        assert result.success

    def test_process_import_with_duplicates(self):
        """Test duplicate detection in import."""
        content = "U01 U02 1\nU01 U02 1\nU03 U04 1\n"
        result = process_import(content)
        assert result.duplicates_skipped == 1