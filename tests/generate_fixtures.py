import datetime
import pathlib
import struct
import sys
import zlib

# Add parent directory to path so we can import ccl_segb modules
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

# Import constants from the main codebase to avoid duplication
from ccl_segb.ccl_segb1 import (
    ALIGNMENT_BYTES_LENGTH as SEGB1_ALIGNMENT,
)
from ccl_segb.ccl_segb1 import (
    HEADER_LENGTH as SEGB1_HEADER_LENGTH,
)
from ccl_segb.ccl_segb2 import (
    ALIGNMENT_BYTES as SEGB2_ALIGNMENT,
)
from ccl_segb.ccl_segb2 import (
    HEADER_LENGTH as SEGB2_HEADER_LENGTH,
)
from ccl_segb.ccl_segb_common import COCOA_EPOCH, MAGIC


def datetime_to_cocoa(dt: datetime.datetime) -> float:
    return (dt - COCOA_EPOCH).total_seconds()

def generate_v1_file(path: pathlib.Path):
    records = [
        (b"TEST_PAYLOAD_001", 1, datetime.datetime(2023, 1, 1, 12, 0, 0), datetime.datetime(2023, 1, 1, 12, 0, 1)),
        (b"TEST_PAYLOAD_002", 1, datetime.datetime(2023, 1, 2, 12, 0, 0), datetime.datetime(2023, 1, 2, 12, 0, 1)),
        (b"DELETED_PAYLOAD", 3, datetime.datetime(2023, 1, 3, 12, 0, 0), datetime.datetime(2023, 1, 3, 12, 0, 1)),
    ]

    with open(path, "wb") as f:
        # Placeholder header
        f.write(b"\x00" * SEGB1_HEADER_LENGTH)
        
        for data, state, ts1, ts2 in records:
            ts1_cocoa = datetime_to_cocoa(ts1)
            ts2_cocoa = datetime_to_cocoa(ts2)
            crc = zlib.crc32(data)
            
            # <iiddIi = int, int, double, double, uint, int
            record_header = struct.pack("<iiddIi", len(data), state, ts1_cocoa, ts2_cocoa, crc, 0)
            f.write(record_header)
            f.write(data)
            
            # Alignment
            padding = (SEGB1_ALIGNMENT - (f.tell() % SEGB1_ALIGNMENT)) % SEGB1_ALIGNMENT
            f.write(b"\x00" * padding)

        end_of_data = f.tell()
        
        # Rewrite header
        f.seek(0)
        # First 4 bytes = end_of_data_offset, last 4 bytes = MAGIC
        header = struct.pack("<I", end_of_data) + b"\x00" * (SEGB1_HEADER_LENGTH - 8) + MAGIC
        f.write(header)

def generate_v2_file(path: pathlib.Path):
    records = [
        (b"V2_PAYLOAD_A", 1, datetime.datetime(2024, 1, 1, 10, 0, 0)),
        (b"V2_PAYLOAD_B", 1, datetime.datetime(2024, 1, 2, 10, 0, 0)),
        (b"V2_DELETED", 3, datetime.datetime(2024, 1, 3, 10, 0, 0)),
    ]
    
    with open(path, "wb") as f:
        # Placeholder header
        f.write(b"\x00" * SEGB2_HEADER_LENGTH)
        
        trailers = []
        
        for data, state, ts in records:
            # Write data entry
            crc = zlib.crc32(data)
            # Entry header: Ii = uint, int
            entry_header = struct.pack("<Ii", crc, 0) # crc, unknown
            f.write(entry_header)
            f.write(data)
            
            end_offset = f.tell() - SEGB2_HEADER_LENGTH # Offset relative to end of header
            
            # Alignment for next record
            padding = (SEGB2_ALIGNMENT - (end_offset % SEGB2_ALIGNMENT)) % SEGB2_ALIGNMENT
            f.write(b"\x00" * padding)
            
            trailers.append((end_offset, state, datetime_to_cocoa(ts)))

        # Write Trailers
        for end_off, state, ts_val in trailers:
            # <2id = int, int, double
            # end_offset, state, timestamp
            trailer = struct.pack("<2id", end_off, state, ts_val)
            f.write(trailer)
            
        # Rewrite Header
        f.seek(0)
        # <4sid16s
        # magic, count, creation_ts, padding
        header = struct.pack("<4sid16s", MAGIC, len(records), datetime_to_cocoa(datetime.datetime.now()), b"\x00"*16)
        f.write(header)

if __name__ == "__main__":
    fixtures_dir = pathlib.Path(__file__).parent / "fixtures"
    fixtures_dir.mkdir(parents=True, exist_ok=True)
    
    print(f"Generating fixtures in {fixtures_dir}...")
    generate_v1_file(fixtures_dir / "v1_mock.bin")
    print("Generated v1_mock.bin")
    generate_v2_file(fixtures_dir / "v2_mock.bin")
    print("Generated v2_mock.bin")
