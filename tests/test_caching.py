from auroconverter.caching import filehash, FileRelatedCache
import pytest as pt
import os.path as pth
from tempfile import NamedTemporaryFile, _TemporaryFileWrapper
import numpy.random as npr
import numpy as np
from string import ascii_letters
import subprocess
from pathlib import Path

TIMES: int = 5
BYTES: int = 100000
"""Count of random bytes to be generated."""

gen: npr.Generator = npr.default_rng()
asciilist: list[str] = list(ascii_letters)

@pt.fixture
def randombytefile(tmp_path):
    with NamedTemporaryFile("w+b") as fp:

        bts: bytes = gen.bytes(BYTES)
        fp.write(bts)
        fp.seek(0)

        yield fp

@pt.fixture
def caching(tmpdir) -> FileRelatedCache:
    return FileRelatedCache(Path(tmpdir))

def test_hash(randombytefile) -> None:
    hsh: str = filehash(randombytefile)
    assert f"{hsh}  {randombytefile.name}\n" == \
        subprocess.run(["md5sum", randombytefile.name], capture_output=True).stdout.decode('utf-8')
    
def test_caching(randombytefile, caching) -> None:
    assert caching.loadcache(randombytefile) is caching.sentinel

    caching.cachedata(randombytefile, "my important data", additional=(5, 0.43, "@"))

    assert caching.loadcache(randombytefile, additional=(5, 0.43, "@")) == "my important data"

    assert caching.loadcache(randombytefile, additional=()) is caching.sentinel





