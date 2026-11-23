"""Optional bundled depth rasterizer for offline exports."""

from __future__ import annotations

from array import array
import ctypes as ct
from functools import lru_cache
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


SOURCE = Path(__file__).with_suffix(".c")


@lru_cache(maxsize=1)
def native_rasterizer():
    compiler = shutil.which("cc")
    if not compiler:
        return None
    with tempfile.TemporaryDirectory(prefix="loopday-depth-") as directory:
        extension = ".dylib" if sys.platform == "darwin" else ".so"
        shared = Path(directory) / ("film_depth" + extension)
        linkage = ["-dynamiclib"] if sys.platform == "darwin" else ["-shared", "-fPIC"]
        command = [compiler, *linkage, "-O3", "-o", str(shared), str(SOURCE), "-lm"]
        try:
            subprocess.run(command, check=True, capture_output=True, timeout=12)
            api = ct.CDLL(str(shared))
        except (OSError, subprocess.SubprocessError):
            return None
        run = api.loopday_raster
        run.argtypes = [ct.c_int, ct.c_int, ct.c_int, ct.c_void_p, ct.c_void_p, ct.c_void_p, ct.c_void_p]
        run.restype = None
        return run


class RasterBuffer:
    def __init__(self, width: int, height: int):
        self.run = native_rasterizer()
        self.width, self.height = width, height
        self.depth = (ct.c_float * (width * height))() if self.run else None
        self.channels = (ct.c_uint8 * (width * height * 3)) if self.run else None

    def draw(self, sky, faces: list):
        from PIL import Image

        if not self.run:
            return None
        coords = array("f")
        rgb = bytearray()
        for shade, vertices in faces:
            color = bytes(int(channel) for channel in shade[4:-1].split(","))
            for index in range(1, len(vertices) - 1):
                coords.extend(vertices[0])
                coords.extend(vertices[index])
                coords.extend(vertices[index + 1])
                rgb.extend(color)
        if not rgb:
            return sky.copy()
        rgb_data = bytearray(sky.tobytes())
        buffer = self.channels.from_buffer(rgb_data)
        polygons = (ct.c_float * len(coords)).from_buffer(coords)
        colors = (ct.c_uint8 * len(rgb)).from_buffer(rgb)
        self.run(self.width, self.height, len(rgb) // 3, polygons, colors, buffer, self.depth)
        return Image.frombytes("RGB", (self.width, self.height), rgb_data)
