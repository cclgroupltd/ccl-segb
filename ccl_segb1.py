import datetime
import struct
import typing
import dataclasses
import pathlib
import os

"""
Copyright 2023, CCL Forensics

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in
the Software without restriction, including without limitation the rights to
use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies
of the Software, and to permit persons to whom the Software is furnished to do
so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""

__version__ = "0.1.2"
__description__ = "A python module to read SEGB v1 files found on iOS, macOS etc."
__contact__ = "Alex Caithness"

MAGIC = b"SEGB"
HEADER_LENGTH = 56
RECORD_HEADER_LENGTH = 32
ALIGNMENT_BYTES_LENGTH = 8
COCOA_EPOCH = datetime.datetime(2001, 1, 1, 0, 0, 0)


@dataclasses.dataclass(frozen=True)
class Segb1Entry:
    timestamp1: datetime.datetime
    timestamp2: datetime.datetime
    data_start_offset: int
    data: bytes


def decode_cocoa_time(seconds) -> datetime.datetime:
    return COCOA_EPOCH + datetime.timedelta(seconds=seconds)


def bytes_to_hexview(b, width=16, show_offset=True, show_ascii=True,
                     line_sep="\n", start_offset=0, max_bytes=-1):
    line_fmt = ""
    if show_offset:
        line_fmt += "{offset:08x}: "
    line_fmt += "{hex}"
    if show_ascii:
        line_fmt += " {ascii}"

    b = b[start_offset:]
    if max_bytes > -1:
        b = b[:max_bytes]

    offset = 0
    lines = []
    while offset < len(b):
        chunk = b[offset:offset + width]
        ascii = "".join(chr(x) if x >= 0x20 and x < 0x7f else "." for x in chunk)
        hex = " ".join(format(x, "02x") for x in chunk).ljust(width * 3)
        line = line_fmt.format(offset=offset, hex=hex, ascii=ascii)
        lines.append(line)
        offset += width

    return line_sep.join(lines)


def read_segb1_stream(stream: typing.BinaryIO) -> typing.Iterable[Segb1Entry]:
    file_header = stream.read(HEADER_LENGTH)
    if len(file_header) != HEADER_LENGTH or file_header[-4:] != MAGIC:
        raise ValueError(f"Unexpected file magic. Expected: {MAGIC.hex()}; got: {file_header[-4:].hex()}")

    end_of_data_offset, = struct.unpack("<I", file_header[0:4])

    while stream.tell() < end_of_data_offset:
        record_header_raw = stream.read(RECORD_HEADER_LENGTH)
        record_length, timestamp1_raw, timestamp2_raw = struct.unpack("<i4xdd", record_header_raw[:24])
        timestamp1 = decode_cocoa_time(timestamp1_raw)
        timestamp2 = decode_cocoa_time(timestamp2_raw)

        record_offset = stream.tell()

        data = stream.read(record_length)
        yield Segb1Entry(timestamp1, timestamp2, record_offset, data)

        # align to 8 bytes
        if (remainder := stream.tell() % ALIGNMENT_BYTES_LENGTH) != 0:
            stream.seek(ALIGNMENT_BYTES_LENGTH - remainder, os.SEEK_CUR)


def read_segb1_file(path: pathlib.Path | os.PathLike | str) -> typing.Iterable[Segb1Entry]:
    path = pathlib.Path(path)
    with path.open("rb") as f:
        yield from read_segb1_stream(f)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print(f"USAGE: {pathlib.Path(sys.argv[0]).name} <SEG2 file>")
        print()
        exit(1)

    for record in read_segb1_file(sys.argv[1]):
        print("=" * 72)
        print(f"Offset: {record.data_start_offset}")
        print(f"Timestamp1: {record.timestamp1}")
        print(f"Timestamp2: {record.timestamp2}")
        print()
        print(bytes_to_hexview(record.data))
        print()
    print("End of records")
    print()
