import datetime
import enum

COCOA_EPOCH = datetime.datetime(2001, 1, 1, 0, 0, 0)
MAGIC = b"SEGB"                # SEGB file signature used by both v1 and v2
MAGIC_SIZE = 4                 # Size of SEGB magic signature in bytes
ASCII_PRINTABLE_START = 0x20   # Start of printable ASCII range (space)
ASCII_PRINTABLE_END = 0x7f     # End of printable ASCII range (DEL)


class EntryState(enum.IntEnum):
    Written = 1
    Deleted = 3
    Empty = 4  # Empty record (v2 only)


def decode_cocoa_time(seconds) -> datetime.datetime:
    """
    Decodes a Cocoa/Mac Absolute timestamp

    :param seconds: the timestamp value in seconds
    :return: the decoded timestamp as a datetime.datetime
    """
    return COCOA_EPOCH + datetime.timedelta(seconds=seconds)


def bytes_to_hexview(b, width=16, show_offset=True, show_ascii=True,
                     line_sep="\n", start_offset=0, max_bytes=-1) -> str:
    """
    Generates a hexview style string for the bytes object b

    :param b: The data (as a bytes object) to be presented as a hexview
    :param width: the width of each line of the hexview in bytes (16 by default)
    :param show_offset: whether to show the offset on the left of the hexview (True by default)
    :param show_ascii: whether to show the ASCII representation of the data on the right of the hexview (True by
    default)
    :param line_sep: string to separate each line of the hexview ('\n' by default)
    :param start_offset: offset to start reading the data from (0 by default)
    :param max_bytes: the maximum number of bytes to render as a hexview or -1 for all of the data (-1 by default)
    :return: a hexview style string for the bytes object b
    """
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
        ascii = "".join(chr(x) if x >= ASCII_PRINTABLE_START and x < ASCII_PRINTABLE_END else "." for x in chunk)
        hex = " ".join(format(x, "02x") for x in chunk).ljust(width * 3)
        line = line_fmt.format(offset=offset, hex=hex, ascii=ascii)
        lines.append(line)
        offset += width

    return line_sep.join(lines)