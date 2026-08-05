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


import dataclasses
import datetime
import os
import pathlib
import struct
import typing
import zlib

from .ccl_segb_common import MAGIC, MAGIC_SIZE, EntryState, decode_cocoa_time

# SEGB v2 File Format Constants (introduced in iOS 17)
# Structure: [32-byte Header][Entries with 8-byte headers + data + 4-byte alignment][16-byte Trailers]
# Key difference from v1: Trailer section at end, smaller headers, different alignment
HEADER_LENGTH = 32            # File header size containing magic, entry count, timestamp
ENTRY_HEADER_LENGTH = 8       # Each entry's header: CRC and unknown value
TRAILER_ENTRY_LENGTH = 16     # Trailer metadata at end of file: offset, state, creation time
ALIGNMENT_BYTES = 4           # Entries padded to 4-byte boundaries (different from v1's 8-byte)


@dataclasses.dataclass(frozen=True)
class EntryMetadata:
    """
    This class relates to the trailer structures
    """
    metadata_offset: int
    end_offset: int
    state: EntryState
    creation: datetime.datetime


@dataclasses.dataclass(frozen=True)
class Segb2Entry:
    metadata: EntryMetadata
    data_start_offset: int
    metadata_crc: int
    actual_crc: int
    data: bytes
    _unknown_value: int = dataclasses.field(kw_only=True, compare=False)

    @property
    def timestamp1(self) -> datetime.datetime:
        return self.metadata.creation

    @property
    def crc_passed(self):
        return self.metadata_crc == self.actual_crc

    @property
    def state(self):
        return self.metadata.state


def stream_matches_segbv2_signature(stream: typing.BinaryIO) -> bool:
    """
    Returns True if the stream contains data matching the SEGB v2 file signature. Resets the stream to the same position
    before returning.

    :param stream: The stream potentially containing SEGB v2 data
    :return: True if the stream contains data matching the SEGB v2 file signature.
    """
    reset_offset = stream.tell()
    file_header = stream.read(HEADER_LENGTH)
    stream.seek(reset_offset, os.SEEK_SET)

    if len(file_header) != HEADER_LENGTH or file_header[0:MAGIC_SIZE] != MAGIC:
        return False

    return True


def file_matches_segbv2_signature(path: pathlib.Path | os.PathLike | str) -> bool:
    """
    Returns True if the file at the given path contains data matching the SEGB v2 file signature. Resets the stream to
    the same position before returning.

    :param path: The path of the file potentially containing SEGB v2 data
    :return: True if the stream contains data matching the SEGB v2 file signature.
    """
    path = pathlib.Path(path)
    with path.open("rb") as f:
        return stream_matches_segbv2_signature(f)


def read_segb2_stream(stream: typing.BinaryIO) -> typing.Iterable[Segb2Entry]:
    """
    Reads SEGB v2 data from a stream and yields an iterable of Segb2Entry objects
    :param stream: a binary stream containing the SEGB data. The data is assumed to begin at the start of the stream
    :return: an iterable of Segb2Entry objects
    """
    trailer_list: list[EntryMetadata] = []

    header_raw = stream.read(HEADER_LENGTH)
    # Parse 32-byte header: <4sid16s = little-endian: 4-byte string, int(4), double(8), 16-byte string
    magic_number, entries_count, creation_timestamp_raw, unknown_padding = struct.unpack("<4sid16s", header_raw)
    if magic_number != MAGIC:
        raise ValueError(f"Unexpected file magic. Expected: {MAGIC.hex()}; got: {magic_number.hex()}")


    # To read the trailer we can just calculate its size and seek from end:
    trailer_reverse_offset = TRAILER_ENTRY_LENGTH * entries_count
    stream.seek(-trailer_reverse_offset, os.SEEK_END)

    for _ in range(entries_count):
        meta_offset = stream.tell()
        trailer_entry_raw = stream.read(TRAILER_ENTRY_LENGTH)
        # Parse 16-byte trailer: <2id = little-endian: 2-byte int, int(4), double(8)
        entry_end_offset, entry_state_raw, entry_timestamp_raw = struct.unpack("<2id", trailer_entry_raw)
        try:
            entry_state = EntryState(entry_state_raw)
        except ValueError:
            # Some SEGB v2 files contain zeroed/unused trailer slots (state 0,
            # end offset 0); they reference no record data, so skip them.
            continue
        trailer_list.append(
            EntryMetadata(
                meta_offset, entry_end_offset, entry_state, decode_cocoa_time(entry_timestamp_raw)))

    # To read the records, in order, get to the end of the header:
    stream.seek(HEADER_LENGTH, os.SEEK_SET)

    # go through the trailer list in order of offset:
    trailer_list.sort(key=lambda x: x.end_offset)
    previous_entry: typing.Optional[Segb2Entry] = None
    for trailer_entry in trailer_list:
        entry_offset = stream.tell()

        # State 4 is an empty record
        if trailer_entry.state == EntryState.Empty:
            continue

        # Two trailer entries can share an end offset (e.g. a record that was
        # written and later marked deleted); both reference the same data
        # region, which has already been read from the stream.
        if previous_entry is not None and trailer_entry.end_offset == previous_entry.metadata.end_offset:
            yield dataclasses.replace(previous_entry, metadata=trailer_entry)
            continue

        # NB end offset is relative to the start of entry area
        entry_length = trailer_entry.end_offset - stream.tell() + HEADER_LENGTH

        # Stale trailer entries (e.g. left behind after the data area was
        # reused) can point inside a region already consumed by a newer
        # record; their original data is gone, so they cannot be read.
        if entry_length < ENTRY_HEADER_LENGTH:
            continue

        entry_raw = stream.read(entry_length)
        data = entry_raw[ENTRY_HEADER_LENGTH:]
        crc32_stored, unknown_raw = struct.unpack("Ii", entry_raw[:ENTRY_HEADER_LENGTH])
        calculated_crc = zlib.crc32(data)

        # align to 4 bytes
        if (remainder := trailer_entry.end_offset % ALIGNMENT_BYTES) != 0:
            stream.seek(ALIGNMENT_BYTES - remainder, os.SEEK_CUR)

        previous_entry = Segb2Entry(trailer_entry, entry_offset, crc32_stored, calculated_crc, data, _unknown_value=unknown_raw)
        yield previous_entry


def read_segb2_file(path: pathlib.Path | os.PathLike | str) -> typing.Iterable[Segb2Entry]:
    """
    Reads SEGB v2 data from a file and yields an iterable of Segb2Entry objects
    :param path: the path of the file to be opened
    :return: an iterable of Segb2Entry objects
    """
    path = pathlib.Path(path)
    with path.open("rb") as f:
        yield from read_segb2_stream(f)

