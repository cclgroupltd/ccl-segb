# ccl-segb
This repo contains Python modules for parsing SEGB (v1 and v2) files and a generic module to automatically determine which to parse based on it's header.

## CLI
All modules may be invoked from the command-line for dumping / previewing 
SEGB files

### Example usage
```commandline
python ccl_segb.py <segb1 or segb2 filename>
```
or
```commandline
python ccl_segb1.py <segb1 filename>
```
or
```commandline
python ccl_segb2.py <segb2 filename>
```

## ccl_segb

### Example usage

```python
import sys
import ccl_segb

# input_path can be a SEGB1 or SEGB2 file
input_path = sys.argv[1]

# A ValueError will be raised if the input_path it not a SEGB1 or SEGB2 file
for record in ccl_segb.read_segb_file(input_path):
    # record will be a SEGB1 or SEGB2 class depending on which type of file was passed
    offset = record.data_start_offset
    state = record.state
    data = record.data
    ts1 = record.timestamp1
    ts2 = record.timestamp2 # Timestamp2 only present if record is a SEGB1
    
    print(offset, state, ts1, ts2)
    print(data.hex())
```

## ccl_segb1

### Example usage

```python
import sys
from ccl_segb import ccl_segb1

input_path = sys.argv[1]

# An open stream can be read using: read_segb1_stream 
for record in ccl_segb1.read_segb1_file(input_path):
    offset = record.data_start_offset
    state = record.state
    data = record.data
    ts1 = record.timestamp1
    ts2 = record.timestamp2

    print(offset, ts1, ts2)
    print(data.hex())
```

## ccl_segb2

### Example usage

```python
import sys
import ccl_segb2

input_path = sys.argv[1]

# An open stream can be read using: read_segb2_stream
for record in ccl_segb2.read_segb2_file(input_path):
    offset = record.data_start_offset
    metadata_offset = record.metadata.metadata_offset
    state = record.metadata.state.name
    ts = record.metadata.creation
    data = record.data
    
    print(offset, metadata_offset, ts, state)
    print(data)

```