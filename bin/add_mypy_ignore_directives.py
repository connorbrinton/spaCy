import re
import subprocess
from pathlib import Path
from typing import List

import typer


# Destructure lines into (i) code, (ii) existing `# type: ignore` directives
# (if any) and (iii) trailing comments (if any)
DIRECTIVE_RE = re.compile(
    r"""(?x)  # Verbose-mode (ignore whitespace and allow comments)
    ^  # We always want to capture beginning at the start of the line
    (?P<code>.*?)  # Everything before trailing comments
    (?P<type_ignore_directive>  # Possible existing `# type: ignore` directive
        \ {1,2}  # Preceded by one or two spaces
        \#\ type:\ ignore\[(?P<error_codes>[^\]]+)\]
    )?
    (?P<trailing_comments>  # Other trailing comments
        \ {1,2}  # Preceded by one or two spaces
        \#\ .*
    )?
    $  # We always want to capture the entire line
    """
)
OLD_RE = """
(?P<directives>  # Directives may occur in any order, so we have a repeating group here
    (?P<separator>\ {1,2})  # Directives may be preceded by one or two spaces
    (?P<directive>
        # Type ignore directives
        (?P<type_ignore_directive>)
        # NoQA directives
        | (?P<noqa_directive>\#\ noqa:[^#]+)
    )
)+
"""

ERROR_RE = re.compile(r"(?P<filepath>.*?):(?P<line_number>\d+): error: .* \[(?P<error_code>[\w\-]+)\]")

def main(
    files: List[Path] = typer.Argument(
        ...,
        exists=True,
        file_okay=True,
        dir_okay=True,
        readable=True,
    )
) -> None:
    """Execute Mypy on the given files and add `# type: ignore[error-code]` directives"""
    # Execute Mypy on the given files
    completed_process = subprocess.run(
        (
            "python",
            "-m",
            "mypy",
            "--show-error-codes",
            *[str(file) for file in files],
        ),
        capture_output=True,
    )

    # Extract structured representation of each error
    for match_groups in ERROR_RE.findall(completed_process.stdout.decode()):
        filepath, line_number, error_code = match_groups

        # Apply # type: ignore[code] directive to the file
        with open(filepath, "r") as source:
            # Read all lines
            lines = source.read().split("\n")

        # Look up the line to modify
        line = lines[int(line_number) - 1]

        # Check for existing directive and corresponding codes
        existing_codes = set()
        trailing_comments = None
        directive_match = DIRECTIVE_RE.match(line)
        if directive_match:
            code = directive_match.group("code")
            existing_codes_str = directive_match.group("error_codes")
            if existing_codes_str:
                existing_codes = set(existing_codes_str.split(", "))
            trailing_comments = directive_match.group("trailing_comments")

        # Add detected code
        error_codes = sorted(existing_codes | {error_code})

        # Build error codes string
        error_codes_str = ", ".join(error_codes)

        # Collect line components
        line_components = [
            code,
            f"# type: ignore[{error_codes_str}]",
        ]
        if trailing_comments:
            line_components.append(trailing_comments)

        # Rebuild line from components
        line = "  ".join(line_components)

        # Store updated line
        lines[int(line_number) - 1] = line

        # Rewrite file
        with open(filepath, "w") as sink:
            sink.write("\n".join(lines))


if __name__ == "__main__":
    typer.run(main)
