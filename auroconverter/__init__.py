from .conv import File, process_image
from .caching import FileRelatedCache
from rich.table import Table
from rich.console import Console
from rich.theme import Theme
from rich.live import Live
from rich.text import Text
from typing import List, Annotated, Optional
from PIL import Image, ImageSequence
from concurrent.futures import ProcessPoolExecutor, Future
from pathlib import Path
from time import perf_counter

from time import sleep
import numpy as np
import typer
import io

app: typer.Typer = typer.Typer()
cache: FileRelatedCache = FileRelatedCache(Path("__auroconv__"))
theme: Theme = Theme({
    "repr.ellipsis": "none",
    "float": "bold cyan"
})
console: Console = Console(theme=theme)




def avgcol(img: np.ndarray, color: bool = True):
    avgcol: np.ndarray | np.floating = np.mean(img, axis=(0, 1), dtype=np.uint64)
    return avgcol if color else (avgcol, ) * 3


def imgtoansi(im: Image.Image, cols: int, scale: float, char: str, color: bool) -> str:
    W, H = im.size
    w: float = W / cols
    h: float = w / scale
    rows: int = int(H / h)
    prev: Optional[int] = None
    
    if not color:
        im = im.convert("L")

    arrim: np.ndarray = np.asarray(im)

    with io.StringIO() as o:
        for j in range(rows):
            y1: int = int(j * h)
            y2: int = H if j == (rows - 1) else int((j + 1) * h)

            for i in range(cols):
                x1: int = int(i * w)
                x2: int = W if i == (cols - 1) else int((i + 1) * w)

                cim: np.ndarray = arrim[y1: y2 + 1, x1: x2 + 1]

                avg: np.ndarray = avgcol(cim, color)

                rgb: int = (
                    avgcol[0] << 16 | avgcol[1] << 8 | avgcol[2]
                )
                
                o.write((
                    f"\033[0m\033[38;2;{avg[0]};{avg[1]};{avg[2]}m{char}" 
                    if prev != rgb else char
                ))

                prev = rgb

            o.write("\n")
            
        return o.getvalue()


@app.command("info")
def info(files: List[File]) -> None:
    """Print information about image."""
    table = Table("Name", "Format", "Size", "Mode")
    with console.status("Processing images..."):
        for file in files:
            im: Image.Image = process_image(file)
            size: tuple[int, int] = im.size
            table.add_row(file.name, im.format, f"{size[0]}x{size[1]}", im.mode)

    console.print(table)


@app.command("ansi")
def ansi(file: File, 
         cols: Annotated[int, typer.Option("--cols", "-c", help="Count of characters in one row.")] = 80, 
         scale: Annotated[float, typer.Option("--scale", "-s", help="Font size.")] = 0.43, 
         char: Annotated[str, typer.Option(help="Character, which will be used to display tiles.")] = "@", 
         color: Annotated[bool, typer.Option(help="Use all kinds of colors.")] = True, 
         caching: Annotated[bool, typer.Option(help="Use cached results.")] = True) -> None:
    """Print ANSI representation of image."""
    start: float = perf_counter()

    console.print("Searching data in cache...")

    frames: list[str] | object = cache.loadcache(file, additional=(cols, scale, char, color)) if caching else cache.sentinel

    if frames is cache.sentinel:
        if caching:
            console.print("[italic bold orange1]No data, starting the processing...[/]")
        else:
            console.print("[italic bold yellow]Caching is disabled![/]")
        with console.status("Processing image..."):
            im: Image.Image = process_image(file)
            with ProcessPoolExecutor() as tp:
                framesf: list[Future] = [
                    tp.submit(imgtoansi, fr.copy(), cols=cols, scale=scale, char=char, color=color) 
                    for fr in ImageSequence.Iterator(im)]
            frames = list(map(lambda f: f.result(), framesf))
            if caching:
                cache.cachedata(file, frames, additional=(
                    cols, scale, char, color
                ))
    else:
        console.print("Data found!")

    # TODO: Use termios or smth in this part
    with console.status("Converting..."):
        framesc: list[Text] = [Text.from_ansi(frame)
                               for frame in frames]

    console.print(f"Done in [float]{perf_counter() - start:.2f}[/]")
    with Live("", refresh_per_second=20, transient=True,
              screen=True) as live:
        while True:
            for frame in framesc:
                live.update(frame)
                sleep(0.05)
