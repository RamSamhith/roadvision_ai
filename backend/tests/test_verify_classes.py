"""Tests for C-04 / AC-08 cross-layer class consistency verifier (D-11).

Verifies that training/verify_classes.py:
1. Rejects 0-byte placeholder files honestly (returns None / PENDING instead of false PASS).
2. Detects missing files and returns None / PENDING.
3. Detects malformed / incomplete class mappings and returns False / FAILED.
4. Accepts valid database schema and frontend files containing canonical classes.
"""

from pathlib import Path
from unittest.mock import patch

import pytest

import training.verify_classes as vc


def test_verify_database_layer_empty_file(tmp_path):
    """0-byte placeholder database files must return None (PENDING), not True (D-11)."""
    empty_sql = tmp_path / "schema.sql"
    empty_sql.write_text("", encoding="utf-8")

    with patch.object(vc, "ROOT_DIR", tmp_path):
        db_dir = tmp_path / "backend" / "app" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "schema.sql").write_text("", encoding="utf-8")

        result = vc.verify_database_layer()
        assert result is None, "0-byte file must report PENDING (None), never True"


def test_verify_database_layer_missing_files(tmp_path):
    """Missing database files must return None (PENDING)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        result = vc.verify_database_layer()
        assert result is None


def test_verify_database_layer_incomplete_classes(tmp_path):
    """Populated database file missing canonical class codes must return False (FAILED)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        db_dir = tmp_path / "backend" / "app" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        # Missing D40
        (db_dir / "schema.sql").write_text("CREATE TABLE t (code TEXT CHECK(code IN ('D00', 'D10', 'D20')));", encoding="utf-8")

        result = vc.verify_database_layer()
        assert result is False


def test_verify_database_layer_valid_contract(tmp_path):
    """Populated database file with all 4 classes must return True (PASSED)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        db_dir = tmp_path / "backend" / "app" / "database"
        db_dir.mkdir(parents=True, exist_ok=True)
        (db_dir / "schema.sql").write_text("CREATE TABLE t (code TEXT CHECK(code IN ('D00', 'D10', 'D20', 'D40')));", encoding="utf-8")

        result = vc.verify_database_layer()
        assert result is True


def test_verify_frontend_layer_empty_file(tmp_path):
    """0-byte placeholder frontend files must return None (PENDING), not True (D-11)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        fe_dir = tmp_path / "frontend" / "src" / "types"
        fe_dir.mkdir(parents=True, exist_ok=True)
        (fe_dir / "classes.ts").write_text("", encoding="utf-8")

        result = vc.verify_frontend_layer()
        assert result is None, "0-byte frontend file must report PENDING (None), never True"


def test_verify_frontend_layer_missing_files(tmp_path):
    """Missing frontend files must return None (PENDING)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        result = vc.verify_frontend_layer()
        assert result is None


def test_verify_frontend_layer_incomplete_classes(tmp_path):
    """Populated frontend file missing canonical class codes must return False (FAILED)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        fe_dir = tmp_path / "frontend" / "src" / "types"
        fe_dir.mkdir(parents=True, exist_ok=True)
        (fe_dir / "classes.ts").write_text("export const CLASSES = ['D00', 'D10'];", encoding="utf-8")

        result = vc.verify_frontend_layer()
        assert result is False


def test_verify_frontend_layer_valid_contract(tmp_path):
    """Populated frontend file with all 4 classes must return True (PASSED)."""
    with patch.object(vc, "ROOT_DIR", tmp_path):
        fe_dir = tmp_path / "frontend" / "src" / "types"
        fe_dir.mkdir(parents=True, exist_ok=True)
        (fe_dir / "classes.ts").write_text("export const CLASSES = ['D00', 'D10', 'D20', 'D40'];", encoding="utf-8")

        result = vc.verify_frontend_layer()
        assert result is True

