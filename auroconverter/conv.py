"""Functions for convinience, which are used only to not write any repeating code."""

from typing import TypeAlias, Annotated
from PIL import Image
from typing import IO
import typer


File: TypeAlias = Annotated[typer.FileBinaryRead, typer.Argument(help="Path to image.")]


def process_image(obj: IO[bytes]):
    """Shortcut for handling the situation when the file isn't a valid image."""
    try:
        img: Image.Image = Image.open(obj)
        return img
    except OSError:
        print(f"Unable to open file '{obj.name}' as Image.")
        raise typer.Abort()