import datetime
import pathlib

import pytest

from ccl_segb import ccl_segb1, ccl_segb2

FIXTURES_DIR = pathlib.Path(__file__).parent / "fixtures"
V1_MOCK = FIXTURES_DIR / "v1_mock.bin"
V2_MOCK = FIXTURES_DIR / "v2_mock.bin"

@pytest.fixture(autouse=True)
def ensure_fixtures():
    """Ensure fixtures exist before running tests."""
    if not V1_MOCK.exists() or not V2_MOCK.exists():
        pytest.fail("Test fixtures not found. Run 'uv run python tests/generate_fixtures.py' first.")

def test_read_segb1():
    """Test reading a SEGB v1 file."""
    records = list(ccl_segb1.read_segb1_file(V1_MOCK))
    
    # We expect 3 records based on generate_fixtures.py
    assert len(records) == 3
    
    # Check Record 1
    assert records[0].data == b"TEST_PAYLOAD_001"
    assert records[0].state == ccl_segb1.EntryState.Written
    assert records[0].timestamp1 == datetime.datetime(2023, 1, 1, 12, 0, 0)
    assert records[0].crc_passed is True

    # Check Record 3 (Deleted)
    assert records[2].data == b"DELETED_PAYLOAD"
    assert records[2].state == ccl_segb1.EntryState.Deleted

def test_read_segb2():
    """Test reading a SEGB v2 file."""
    records = list(ccl_segb2.read_segb2_file(V2_MOCK))
    
    # We expect 3 records based on generate_fixtures.py
    assert len(records) == 3

    # Check Record 1
    assert records[0].data == b"V2_PAYLOAD_A"
    assert records[0].state == ccl_segb2.EntryState.Written
    assert records[0].timestamp1 == datetime.datetime(2024, 1, 1, 10, 0, 0)
    assert records[0].crc_passed is True

    # Check Record 3 (Deleted)
    assert records[2].data == b"V2_DELETED"
    assert records[2].state == ccl_segb2.EntryState.Deleted
