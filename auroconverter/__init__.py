from .conv import File, spinning_progress, process_image
from .caching import FileRelatedCache
from rich.table import Table
from rich import print as rprint
from typing import List, Annotated
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

def avgcol(img: np.ndarray, color: bool = True):
    avgcol: np.ndarray | np.floating = np.mean(img, axis=(0, 1))
    return avgcol if color else (avgcol, ) * 3


def imgtoansi(im: Image.Image, cols: int, scale: float, char: str, color: bool) -> str:
    W, H = im.size
    w: float = W / cols
    h: float = w / scale
    rows: int = int(H // h)
    
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
                o.write(f"\x1b[38;2;{int(avg[0])};{int(avg[1])};{int(avg[2])}m{char}") # char = @

            o.write("\n")

        res: str = o.getvalue()

    return res




@app.command("info")
def info(files: List[File]) -> None:
    """Print information about image."""
    table = Table("Name", "Format", "Size", "Mode")
    with spinning_progress() as progress:
        progress.add_task("Processing images...")
        for file in files:
            im: Image.Image = process_image(file)
            size: tuple[int, int] = im.size
            table.add_row(file.name, im.format, f"{size[0]}x{size[1]}", im.mode)

    rprint(table)




@app.command("ansi")
def ansi(file: File, 
         cols: Annotated[int, typer.Option("--cols", "-c", help="Count of characters in one row.")] = 80, 
         scale: Annotated[float, typer.Option("--scale", "-s", help="Font size.")] = 0.43, 
         char: Annotated[str, typer.Option("--char", help="Character, which will be used to display tiles.")] = "@", 
         anim: Annotated[bool, typer.Option("--anim", "-a", help="Display image as animation.")] = False,
         color: Annotated[bool, typer.Option("--color", help="Use all kinds of colors.")] = True, 
         caching: Annotated[bool, typer.Option("--caching", help="Use cached results.")] = True) -> None:
    """Print ANSI representation of image."""
    start: float = perf_counter()

    rprint("[italic grey78]Searching data in cache...[/]")

    frames: list[str] | object = cache.loadcache(file, additional=(cols, scale, char, color)) if caching else cache.sentinel

    if frames is cache.sentinel:
        if caching:
            rprint("[italic bold orange1]No data, starting the processing...[/]")
        else:
            rprint("[italic bold yellow]Caching is disabled![/]")
        with spinning_progress() as progress:
            progress.add_task("Processing image...")
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
        rprint("[italic bold cyan1]Data found![/]")

    rprint(f"[italic grey78]Done in [bold cyan1]{perf_counter() - start:.2f}[/] seconds.[/]")
    if anim:
        i: int = 0
        frl: int = len(frames) - 1
        frheight: int = frames[0].count("\n") + 2
        rprint(f"[italic grey78]There are [bold cyan1]{frheight}[/] rows.[/]")
        try:
            while True:
                print(frames[i])
                print(f"\x1b[{frheight}F")
                sleep(0.05)
                i = 0 if i == frl else i + 1
        except KeyboardInterrupt:
            print(f"\x1b[{frheight}M\x1b[0m", end="")
            rprint("[italic grey78]Done![/]")
    else:
        print(frames[0])
        print("\x1b[0m")
