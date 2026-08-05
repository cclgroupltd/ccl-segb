import json
import pathlib

import blackboxprotobuf
import typer
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from ccl_segb import ccl_segb, ccl_segb_common
from ccl_segb.ccl_segb1 import Segb1Entry
from ccl_segb.ccl_segb2 import Segb2Entry

app = typer.Typer(
    help="A tool for parsing and dumping SEGB v1 and v2 files from iOS, macOS, etc.",
    no_args_is_help=True
)
console = Console()
console_err = Console(stderr=True)

@app.command()
def dump(
    file_path: pathlib.Path = typer.Argument(..., exists=True, dir_okay=False, help="Path to the SEGB file to analyze"),
    json_output: bool = typer.Option(False, "--json", help="Output records as JSON lines instead of formatted tables"),
    decode_protobuf: bool = typer.Option(False, "--decode-protobuf", help="Attempt to decode data payloads as Protocol Buffers"),
):
    """
    Parse and display the contents of a SEGB file.
    
    Automatically detects SEGB v1 or v2 format and displays all records
    with their metadata, timestamps, and data payloads.
    """
    # Use stderr for informational messages in JSON mode to allow clean piping
    output_console = console_err if json_output else console
    
    try:
        # Use the library function to auto-detect format and read records
        records = list(ccl_segb.read_segb_file(file_path))
        
        if not records:
            console.print("[bold yellow]Warning: No records found in file[/bold yellow]")
            return
        
        # Determine version based on first record type
        first_record = records[0]
        if isinstance(first_record, Segb1Entry):
            output_console.print(f"[bold green]Detected SEGB v1 file: {file_path}[/bold green]")
            _process_v1_records(records, json_output, decode_protobuf)
        elif isinstance(first_record, Segb2Entry):
            output_console.print(f"[bold green]Detected SEGB v2 file: {file_path}[/bold green]")
            _process_v2_records(records, json_output, decode_protobuf)
    except ValueError as e:
        console.print(f"[bold red]Error: {e}[/bold red]")
        raise typer.Exit(code=1)

def _decode_protobuf_data(data: bytes) -> tuple[dict | None, dict | None]:
    """Attempt to decode data as protobuf. Returns (decoded_message, typedef) or (None, None) on failure."""
    try:
        message, typedef = blackboxprotobuf.protobuf_to_json(data)
        # Parse the JSON string back to a dict for easier handling
        return json.loads(message), typedef
    except Exception:
        return None, None

def _process_v1_records(records: list[Segb1Entry], json_output: bool, decode_protobuf: bool):
    if json_output:
        for record in records:
            data = {
                "offset": record.data_start_offset,
                "timestamp1": record.timestamp1.isoformat(),
                "timestamp2": record.timestamp2.isoformat(),
                "state": record.state.name,
                "crc_passed": record.crc_passed,
                "data_hex": record.data.hex()
            }
            if decode_protobuf:
                decoded, typedef = _decode_protobuf_data(record.data)
                if decoded:
                    data["protobuf_decoded"] = decoded
                    data["protobuf_typedef"] = typedef
            print(json.dumps(data))
    else:
        for record in records:
            table = Table(box=box.SIMPLE)
            table.add_column("Field", style="cyan")
            table.add_column("Value")
            
            table.add_row("Offset", str(record.data_start_offset))
            table.add_row("Timestamp1", str(record.timestamp1))
            table.add_row("Timestamp2", str(record.timestamp2))
            table.add_row("State", record.state.name)
            table.add_row("CRC Passed", str(record.crc_passed))
            
            console.print(table)
            
            if decode_protobuf:
                decoded, _ = _decode_protobuf_data(record.data)
                if decoded:
                    console.print("\n[bold yellow]Decoded Protobuf:[/bold yellow]")
                    syntax = Syntax(json.dumps(decoded, indent=2), "json", theme="monokai", line_numbers=False)
                    console.print(Panel(syntax, border_style="yellow"))
                    console.print()
            
            console.print(ccl_segb_common.bytes_to_hexview(record.data))
            console.print("=" * 72)

def _process_v2_records(records: list[Segb2Entry], json_output: bool, decode_protobuf: bool):
    if json_output:
        for record in records:
            data = {
                "offset": record.data_start_offset,
                "creation_timestamp": record.metadata.creation.isoformat(),
                "state": record.metadata.state.name,
                "crc_passed": record.crc_passed,
                "data_hex": record.data.hex()
            }
            if decode_protobuf:
                decoded, typedef = _decode_protobuf_data(record.data)
                if decoded:
                    data["protobuf_decoded"] = decoded
                    data["protobuf_typedef"] = typedef
            print(json.dumps(data))
    else:
        for record in records:
            table = Table(box=box.SIMPLE)
            table.add_column("Field", style="cyan")
            table.add_column("Value")

            table.add_row("Offset", str(record.data_start_offset))
            table.add_row("Creation Timestamp", str(record.metadata.creation))
            table.add_row("State", record.metadata.state.name)
            table.add_row("CRC Passed", str(record.crc_passed))

            console.print(table)
            
            if decode_protobuf:
                decoded, _ = _decode_protobuf_data(record.data)
                if decoded:
                    console.print("\n[bold yellow]Decoded Protobuf:[/bold yellow]")
                    syntax = Syntax(json.dumps(decoded, indent=2), "json", theme="monokai", line_numbers=False)
                    console.print(Panel(syntax, border_style="yellow"))
                    console.print()

            console.print(ccl_segb_common.bytes_to_hexview(record.data))
            console.print("=" * 72)

if __name__ == "__main__":
    app()
