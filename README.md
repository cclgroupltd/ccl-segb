# ccl-segb
This repo contains Python modules for parsing SEGB (v1 and v2) files.

## CLI
Both modules may be invoked from the command-line for dumping / previewing 
SEGB files

## ccl_segb1

### Example usage

```python
import sys
import ccl_segb1

input_path = sys.argv[1]

# An open stream can be read using: read_segb1_stream 
for record in ccl_segb1.read_segb1_file(input_path):
    offset = record.data_start_offset
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