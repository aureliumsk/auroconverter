from .conv import File, spinning_progress, process_image
from .caching import FileRelatedCache, filehash
from rich.table import Table
from typing import List
from PIL import Image, ImageSequence
from concurrent.futures import ProcessPoolExecutor, Future
from pathlib import Path
from time import perf_counter

from time import sleep
import numpy as np
import typer
import rich
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

    rich.print(table)




@app.command("ansi")
def ansi(file: File, cols: int = 80, scale: float = 0.43, char: str = "@", anim: bool = False,
         color: bool = True) -> None:
    """Print ANSI repr of image."""
    start: float = perf_counter()

    print("Searching data in cache...")

    frames: list[str] | object = cache.loadcache(file, additional=(cols, scale, char, color))

    if frames is cache.sentinel:
        print("No data, starting the processing...")
        with spinning_progress() as progress:
            progress.add_task("Processing image...")
            im: Image.Image = process_image(file)
            with ProcessPoolExecutor() as tp:
                framesf: list[Future] = [
                    tp.submit(imgtoansi, fr.copy(), cols=cols, scale=scale, char=char, color=color) 
                    for fr in ImageSequence.Iterator(im)]
            frames = list(map(lambda f: f.result(), framesf))
            cache.cachedata(file, frames, additional=(
                cols, scale, char, color
            ))
    else:
        print("Data found.")

    print(f"Done in {perf_counter() - start:.2f}s.")
    if anim:
        i: int = 0
        frl: int = len(frames) - 1
        frheight: int = frames[0].count("\n") + 2
        print(f"There are {frheight} rows.")
        try:
            while True:
                print(frames[i])
                print(f"\x1b[{frheight}F")
                i = 0 if i == frl else i + 1
        except KeyboardInterrupt:
            print(f"\x1b[{frheight}M\x1b[0mDone!")
    else:
        print(frames[0])
        print("\x1b[0m")
