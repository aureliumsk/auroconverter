from hashlib import md5
from io import BufferedIOBase
from pathlib import Path
from typing import Any, Optional
from struct import pack
import os
import gzip as gz
import pickle

typemap: dict[type, str] = {
    float: "d",
    int: "i",
    bool: "?"
}


def filehash(fp: BufferedIOBase,
             buffer_length: int = 2**18, additional: tuple = ()) -> str:
    """
    Generate hash of a file and return hexacedimal representation of it.

    @param fp: Readable file stream opened() in binary mode.
    @param buffer_length: Count of bytes which will be read from file at once.
    @param additional: Additional values (supported types are: int, str, float), which will be added to hash.

    """

    buffer: bytearray = bytearray(buffer_length)
    view: memoryview = memoryview(buffer)
    hasher = md5()

    if not hasattr(fp, 'readinto'):
        raise ValueError("fp isn't a file stream opened in binary mode!")

    fp.seek(0)

    while size := fp.readinto(buffer):
        hasher.update(view[:size])
    
    for value in additional:
        hasher.update(
            bytes(value, 'utf-8') if isinstance(value, str) else pack(typemap[type(value)], value) 
        )


    return hasher.hexdigest()

      
class FileRelatedCache:
    sentinel: object = object()
    """Defaut value, returned if cache doesn't/already exists."""

    def __init__(self, dir: Path) -> None:
        self.dir = dir
        """Directory of cache files."""
        self.cch = [fl for fl in dir.glob("*.gz")]
        """Currently available cache."""
        if not self.dir.exists():
            self.dir.mkdir()

    def cachedata(self, file: BufferedIOBase, data: Any, default: Any = sentinel,
                  additional: tuple = ()):
        """Save some data"""
        hsh: str = filehash(file, additional=additional)

        pth: Path = self.dir / f"{hsh}.gz"

        if pth in self.cch:
            return default
        
        with gz.open(pth, "xb") as fp:
            pickle.dump(data, fp)

        self.cch.append(pth)

    def loadcache(self, file: BufferedIOBase, default: Any = sentinel,
                  additional: tuple = ()) -> Any:
        """Load some data."""
        hsh: str = filehash(file, additional=additional)
        
        pth: Path = self.dir / f"{hsh}.gz"

        if not (pth in self.cch):
            return default
        
        with gz.open(pth, "rb") as fp:
            data: Any = pickle.load(fp)

        return data

