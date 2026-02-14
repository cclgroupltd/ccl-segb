# ccl-segb

A Python library and CLI tool for parsing SEGB (v1 and v2) files found on iOS, macOS, and other Apple platforms.

## What are SEGB files?

SEGB files are binary data stores used by Apple's **Biome** system, a framework that records structured event data across Apple devices. These files contain timestamped records of user activity such as Siri interactions, call history, media playback, app usage, and more.

SEGB files can be found at:

- **macOS:** `~/Library/Biome/streams/`
- **iOS:** Accessible via forensic extraction or device backups

There are two format versions:

- **SEGB v1** — used in earlier iOS/macOS versions
- **SEGB v2** — introduced in iOS 17, with a different header structure and trailer-based metadata

## Installation

### From GitHub (recommended)

```bash
# Clone the repository
git clone https://github.com/cclgroupltd/ccl-segb.git
cd ccl-segb

# Install dependencies and the package
uv sync
```

### As a dependency in another project

```bash
uv add git+https://github.com/cclgroupltd/ccl-segb.git
```

Or with pip:

```bash
pip install git+https://github.com/cclgroupltd/ccl-segb.git
```

## Dependencies

| Package | Purpose |
|---------|---------|
| [typer](https://typer.tiangolo.com/) | CLI framework with auto-generated help and shell completion |
| [rich](https://rich.readthedocs.io/) | Formatted terminal output (tables, syntax highlighting) |
| [bbpb](https://github.com/nickheal/bbpb) | Protocol Buffers decoding for SEGB data payloads |

All dependencies are installed automatically via `uv sync` or `pip install`.

## CLI

A command-line tool is provided for parsing and previewing SEGB files.

```
Usage: ccl-segb [OPTIONS] FILE_PATH

Options:
  --json                Output records as JSON lines instead of formatted tables
  --decode-protobuf     Attempt to decode data payloads as Protocol Buffers
  --help                Show this message and exit.
```

### Examples

Basic usage (formatted table output):

```bash
ccl-segb path/to/segb_file
```

JSON output (useful for piping to `jq`):

```bash
ccl-segb path/to/segb_file --json | jq '.'
```

JSON output with protobuf decoding:

```bash
ccl-segb path/to/segb_file --json --decode-protobuf | jq '{state, crc_passed, protobuf_decoded}'
```

## Library Usage

### Auto-detecting format

The simplest way to use the library, automatically detects whether the file is SEGB v1 or v2:

```python
import ccl_segb

for record in ccl_segb.read_segb_file("path/to/segb_file"):
    print(record.data_start_offset, record.state.name)
    print(record.data.hex())
```

### SEGB v1

```python
from ccl_segb import ccl_segb1

for record in ccl_segb1.read_segb1_file("path/to/segb_v1_file"):
    print(record.data_start_offset)
    print(record.state.name)           # Written, Deleted, etc.
    print(record.timestamp1)
    print(record.timestamp2)
    print(record.crc_passed)
    print(record.data.hex())
```

### SEGB v2

```python
from ccl_segb import ccl_segb2

for record in ccl_segb2.read_segb2_file("path/to/segb_v2_file"):
    print(record.data_start_offset)
    print(record.metadata.state.name)  # Written, Deleted, etc.
    print(record.metadata.creation)    # Creation timestamp
    print(record.crc_passed)
    print(record.data.hex())
```

## Development

```bash
# Install with dev dependencies
uv sync

# Run tests
uv run pytest

# Lint
uv run ruff check .
```

## Migrating from v0.3 to v0.4.0

### Breaking Changes

- **`EntryState.Unknown` renamed to `EntryState.Empty`**: State 4 records in SEGB v2 are empty records. Code referencing `EntryState.Unknown` should be updated to `EntryState.Empty`.

- **`ccl_segb_cli.py` removed**: The standalone CLI script has been replaced by an installable `ccl-segb` command powered by [Typer](https://typer.tiangolo.com/). Use `ccl-segb <file>` instead of `python ccl_segb_cli.py <file>`.

- **`run_command()` removed from `ccl_segb1` and `ccl_segb2`**: These functions were internal CLI helpers. Use the `ccl-segb` command or the library API (`read_segb_file`, `read_segb1_file`, `read_segb2_file`) instead.

- **`setup.py` replaced by `pyproject.toml`**: The project now uses [Hatchling](https://hatch.pypa.io/) as the build backend. Install with `uv sync` or `pip install .`.

- **Python ≥ 3.10 now required**: Previously implicit, now declared explicitly in `pyproject.toml`.

## License

MIT License.

*Copyright 2023, CCL Forensics*

*Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:*

*The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.*

*THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.*