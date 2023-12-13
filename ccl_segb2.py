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

# This module is based upon information provided by Cellebrite,
# found at: https://cellebrite.com/en/understanding-and-decoding-the-newest-ios-segb-format/
# Thank you for posting the research!


import os
import pathlib
import struct
import enum
import dataclasses
import typing
import datetime

__version__ = "0.1"
__description__ = "A python module to read SEGB v2 files found on iOS, macOS etc."
__contact__ = "Alex Caithness"

HEADER_LENGTH = 32
TRAILER_ENTRY_LENGTH = 16
MAGIC = b"SEGB"
COCOA_EPOCH = datetime.datetime(2001, 1, 1, 0, 0, 0)


class EntryState(enum.IntEnum):
    Written = 1
    Deleted = 3


@dataclasses.dataclass(frozen=True)
class EntryMetadata:
    metadata_offset: int
    end_offset: int
    state: EntryState
    creation: datetime.datetime


@dataclasses.dataclass(frozen=True)
class Segb2Entry:
    metadata: EntryMetadata
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


def read_segb2_stream(stream: typing.BinaryIO) -> typing.Iterable[Segb2Entry]:
    trailer_list: list[EntryMetadata] = []

    header_raw = stream.read(HEADER_LENGTH)
    magic_number, entries_count, creation_timestamp_raw, unknown_padding = struct.unpack("<4sid16s", header_raw)
    if magic_number != MAGIC:
        raise ValueError(f"Unexpected file magic. Expected: {MAGIC.hex()}; got: {magic_number}")

    creation_date = decode_cocoa_time(creation_timestamp_raw)  # nothing done with this at the moment...

    # To read the trailer we can just calculate its size and seek from end:
    trailer_reverse_offset = TRAILER_ENTRY_LENGTH * entries_count
    stream.seek(-trailer_reverse_offset, os.SEEK_END)

    for _ in range(entries_count):
        meta_offset = stream.tell()
        trailer_entry_raw = stream.read(TRAILER_ENTRY_LENGTH)
        entry_end_offset, entry_state_raw, entry_timestamp_raw = struct.unpack("<2id", trailer_entry_raw)
        trailer_list.append(
            EntryMetadata(
                meta_offset, entry_end_offset, EntryState(entry_state_raw), decode_cocoa_time(entry_timestamp_raw)))

    # To read the records, in order, get to the end of the header:
    stream.seek(HEADER_LENGTH, os.SEEK_SET)

    # go through the trailer list in order of offset:
    trailer_list.sort(key= lambda x: x.end_offset)
    for trailer_entry in trailer_list:
        entry_offset = stream.tell()

        # NB end offset is relative to the start of entry area
        entry_length = trailer_entry.end_offset - stream.tell() + HEADER_LENGTH

        entry_raw = stream.read(entry_length)

        # align to 4 bytes
        if (remainder := trailer_entry.end_offset % 4) != 0:
            stream.seek(4 - remainder, os.SEEK_CUR)

        yield Segb2Entry(trailer_entry, entry_offset, entry_raw)


def read_segb2_file(path: pathlib.Path | os.PathLike | str) -> typing.Iterable[Segb2Entry]:
    path = pathlib.Path(path)
    with path.open("rb") as f:
        yield from read_segb2_stream(f)


if __name__ == '__main__':
    import sys

    if len(sys.argv) < 2:
        print(f"USAGE: {pathlib.Path(sys.argv[0]).name} <SEG2 file>")
        print()
        exit(1)

    for record in read_segb2_file(sys.argv[1]):
        print("=" * 72)
        print(f"Offset: {record.data_start_offset}")
        print(f"Creation Timestamp: {record.metadata.creation}")
        print(f"State: {record.metadata.state.name}")
        print()
        print(bytes_to_hexview(record.data))
        print()
    print("End of records")
    print()
