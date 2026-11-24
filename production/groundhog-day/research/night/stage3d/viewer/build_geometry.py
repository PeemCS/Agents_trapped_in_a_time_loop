"""Extract the supported blocking primitives from this rehearsal's emitted USDA."""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
PRIM = re.compile(r'def (Xform|Cube|Cone|Cylinder|Sphere|Camera) "([^"]+)" \{')
VECTOR = re.compile(r'(?:float3|double3) xformOp:(translate|scale) = \(([^)]+)\)')
COLOR = re.compile(r'color3f\[\] primvars:displayColor = \[\(([^)]+)\)\]')


def vector(raw):
    return [float(x) for x in raw.split(",")]


def extract(stage):
    roots = []
    stack = []
    in_samples = False
    for line in stage.splitlines():
        line = line.strip()
        if in_samples:
            if line == "}":
                in_samples = False
            continue
        if ".timeSamples = {" in line:
            in_samples = True
            continue
        if match := PRIM.fullmatch(line):
            prim = {"type": match[1], "name": match[2], "children": []}
            (stack[-1]["children"] if stack else roots).append(prim)
            stack.append(prim)
        elif line == "}" and stack:
            stack.pop()
        elif stack and (match := VECTOR.fullmatch(line)):
            stack[-1][match[1]] = vector(match[2])
        elif stack and (match := COLOR.fullmatch(line)):
            stack[-1]["color"] = vector(match[1])
    if stack or len(roots) != 1 or roots[0]["name"] != "Stage":
        raise ValueError("Unable to read the canonical Stage root")
    return {p["name"]: p for p in roots[0]["children"]}


def descendants(node, path=()):
    here = (*path, node["name"])
    if node["type"] != "Xform":
        if node["type"] not in {"Cube", "Cone", "Cylinder", "Sphere"}:
            raise ValueError(f"Unexpected geometry primitive {here}")
        yield {"path": "/".join(here), "type": node["type"], "position": node["translate"],
               "size": node["scale"], "color": node["color"]}
    for child in node["children"]:
        yield from descendants(child, here)


def main():
    stage_path = HERE.parent / "rehearsal/another-tuesday.usda"
    manifest = json.loads((stage_path.parent / "shot-manifest.json").read_text())
    root = extract(stage_path.read_text())
    data = {"usda_sha256": hashlib.sha256(stage_path.read_bytes()).hexdigest(),
            "performance_sha256": manifest["source_sha256"], "sets": {}, "rigs": {}}
    for key, name in [("town", "MillCreek"), ("city", "Pittsburgh")]:
        prim = root[name]
        data["sets"][key] = {"offset": prim["translate"], "shapes": list(descendants(prim))}
    for role, prim in zip(("reporter", "producer", "camera"), root["Cast"]["children"], strict=True):
        joints = {p["name"]: p["translate"] for p in prim["children"] if p["type"] == "Xform"}
        data["rigs"][role] = {"joints": joints, "shapes": list(descendants(prim))}
    data["coach"] = list(descendants(root["Coach"]))
    out = HERE / "geometry.js"
    out.write_text("window.TUESDAY_STAGE = " + json.dumps(data,separators=(",", ":")) + ";\n")
    print({scene: len(s["shapes"]) for scene,s in data["sets"].items()}, {r:len(x["shapes"]) for r,x in data["rigs"].items()})


if __name__ == "__main__":
    main()
