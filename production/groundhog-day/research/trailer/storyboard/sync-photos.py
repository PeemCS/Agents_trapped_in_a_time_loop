#!/usr/bin/env python3
"""Collect this production's image results and refresh the review gallery."""
import argparse
import hashlib
import json
import re
import subprocess
import tempfile
from datetime import datetime
from html import escape, unescape
from pathlib import Path
from shutil import copyfileobj
from urllib.parse import urlsplit
from urllib.request import urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent
REGISTER = ROOT / "photo-register.json"
INDEX = ROOT / "index.html"
SELECTIONS = ROOT / "photo-selections.json"
PRODUCTION = "Production still for an intimate 1993 Pennsylvania winter drama."
SLATE = re.compile(r"Continuity slate ([A-Z0-9-]+)\. ")
CARD = re.compile(r'(<article class="photo-card" id="card-([^-]+)-[^"]+">)(.*?)</article>', re.S)
CARD_ID = re.compile(r'<div class="card-id">([A-Za-z0-9-]+)')
ALT = re.compile(r"^(.+?)-ALT(?:-?\d+)?$")
EXTRA_SLATES = {
    "S01-D1-MATCH", "S02-C1-SIDE", "S02-D-CALL", "S04-B2-FIX", "S04-B2-POLISH",
    "S04-B2-SHADE", "S04-C-POLISH", "S04-C-SHADE", "S04-D2-LARRY", "S05-A-WHEEL",
    "S05-WAIT-START", "S05-WAIT-RETURN",
}


def write(path, content):
    if path.read_text() != content:
        with tempfile.TemporaryDirectory(dir=path.parent) as directory:
            temp = Path(directory) / path.name
            temp.write_text(content)
            temp.replace(path)


def download(url, path):
    if urlsplit(url).scheme != "https":
        raise ValueError("Image result must use HTTPS")
    with tempfile.TemporaryDirectory(dir=path.parent) as directory:
        original = Path(directory) / "source"
        jpeg = Path(directory) / "review.jpg"
        with urlopen(url, timeout=25) as response, original.open("wb") as destination:
            copyfileobj(response, destination)
        subprocess.run(
            ["sips", "-s", "format", "jpeg", "-s", "formatOptions", "92",
             str(original), "--out", str(jpeg)],
            check=True, stdout=subprocess.DEVNULL,
        )
        jpeg.replace(path)


def sync_jobs(rows, gallery_ids):
    raw = subprocess.check_output(
        ["higgsfield", "generate", "list", "--image", "--size", "100", "--json"],
        text=True, timeout=30,
    )
    by_job = {row["job"]: row for row in rows}
    by_id = {row["id"]: row for row in rows}
    for job in reversed(json.loads(raw)):
        params = job.get("params", {})
        prompt = params.get("prompt") or ""
        if PRODUCTION not in prompt:
            continue
        row = by_job.get(job["id"])
        if row is None:
            match = SLATE.search(prompt)
            if not match:
                continue
            identifier = match[1]
            alt = ALT.fullmatch(identifier)
            base = alt[1] if alt else identifier
            if base not in gallery_ids and not re.fullmatch(r"[A-Z0-9]+-(?:M|MASTER)", base):
                continue
            suffix = 1
            while identifier in by_id:
                identifier = f"{base}-ALT{suffix}"
                suffix += 1
            references = [
                media["data"]["id"] for media in params.get("medias", [])
                if media.get("data", {}).get("type") == "image_job"
            ]
            row = {"id": identifier, "job": job["id"], "status": job["status"],
                   "references": references, "file": None, "prompt": prompt}
            rows.append(row)
            by_id[identifier] = row
            by_job[job["id"]] = row
        row["status"] = job["status"]
        if job["status"] != "completed" or not job.get("result_url"):
            continue
        filename = row["file"] or f'photos/{row["id"]}.jpg'
        path = ROOT / filename
        if not path.exists():
            try:
                download(job["result_url"], path)
                print(f'Downloaded {row["id"]}', flush=True)
            except (OSError, subprocess.SubprocessError, ValueError) as error:
                print(f'Could not download {row["id"]} ({type(error).__name__})', flush=True)
                continue
        row["file"] = filename

    rows.sort(key=lambda row: row["id"])
    write(REGISTER, json.dumps(rows, ensure_ascii=False, indent=2) + "\n")


def media(path, label, group, loading="lazy"):
    path, label = escape(path), escape(label)
    return (f'<button type="button" class="media photo" data-zoom="{path}" data-label="{label}"'
            f' data-group="{group}" aria-label="Enlarge {label}">'
            f'<img src="{path}" alt="{label}" loading="{loading}" decoding="async">'
            '<span class="expand" aria-hidden="true">⤢</span></button>')


def rebuild(html, rows, selections):
    qa = json.loads((ROOT / "photo-qa.json").read_text())
    statuses = {row["id"]: row["status"] for row in rows}
    qa_labels = {"ready": "QA checked", "revise": "QA changes advised", "study": "Study"}
    files = {row["id"]: row["file"] for row in rows
             if row.get("file") and (ROOT / row["file"]).is_file()}
    for choice in selections.values():
        for identifier, path in choice.get("local_studies", {}).items():
            if (ROOT / path).is_file():
                files[identifier] = path
        if choice.get("local_file") and (ROOT / choice["local_file"]).is_file():
            files[choice["use"]] = choice["local_file"]
    mapped, sequence, available = set(), set(), set()
    previous_additions = set()
    fingerprints, hashes = {}, {}
    selected = {shot: choice["use"] for shot, choice in selections.items() if choice["use"] in files}
    originals = {f"{shot}-ORIGINAL": shot for shot in selected if shot in files}

    def image_or_placeholder(identifier, path, label, group, loading="lazy"):
        if path:
            return media(path, label, group, loading)
        state = {
            "queued": "Queued", "processing": "Generating", "running": "Generating",
            "in_progress": "Generating", "failed": "Generation failed",
            "completed": "Awaiting download",
        }.get(statuses.get(identifier), "Awaiting photo")
        return f'<div class="empty" aria-label="{escape(label)}: {state}"><span>{state}</span></div>'

    def review(identifier, path, source):
        if path is None:
            return '<div class="pending-choice">Review opens when the image arrives</div>'
        finding = qa.get(source, qa.get(identifier, {}))
        state = finding.get("status", "pending")
        guidance = selections.get(identifier, {}).get("note", "")
        notes = " ".join(filter(None, (finding.get("note"), guidance)))
        note = f" · {escape(notes)}" if notes else ""
        if path not in hashes:
            hashes[path] = hashlib.sha256((ROOT / path).read_bytes()).hexdigest()[:16]
        fingerprints[identifier] = hashes[path]
        return (f'<p class="qa {escape(state)}"><b>{qa_labels.get(state, "QA pending")}</b>{note}</p>'
                f'<label class="choice">Your decision<select data-approval="{identifier}"'
                f' data-fingerprint="{hashes[path]}" aria-label="Your decision for {identifier}">'
                '<option value="pending">Pending review</option><option value="approved">Approved</option>'
                '<option value="revise">Request changes</option></select></label>')

    def render_card(match):
        opening, group, inner = match.groups()
        identifier = CARD_ID.search(inner)[1]
        if group == "additional":
            previous_additions.add(identifier)
            return match[0]
        title = re.search(r"<h4>(.*?)</h4>", inner)[1]
        label = f"{identifier} · {unescape(title)}"
        source = selected.get(identifier, "S00-D" if identifier == "S02-E1" else identifier)
        path = files.get(source)
        mapped.add(identifier)
        if identifier in selected:
            mapped.add(source)
        if identifier.startswith(group + "-"):
            sequence.add(identifier)
            if path:
                available.add(identifier)
        decision = review(identifier, path, source)
        upgrades = [
            alt_id for alt_id in files
            if alt_id != source and (base := ALT.fullmatch(alt_id)) and base[1] == identifier
            and qa.get(alt_id, {}).get("status") == "ready"
        ]
        if upgrades:
            links = " · ".join(f'<a href="#card-additional-{alt_id}">{alt_id}</a>' for alt_id in upgrades)
            decision += f'<p class="alternates">QA-checked alternatives · {links}</p>'
        original = f"{identifier}-ORIGINAL"
        if original in originals:
            title_link = escape(selections[identifier]["original_title"])
            decision += f'<p class="alternates"><a href="#card-additional-{original}">{title_link}</a></p>'
        brief = re.search(r'<details class="prompt">.*?</details>', inner, re.S)
        attribution = f'<small class="reuse">Source {source}</small>' if source != identifier else ""
        return (f'{opening}{image_or_placeholder(identifier, path, label, group)}'
                f'<div class="card-body"><div class="card-id">{identifier}{attribution}'
                f'</div><h4>{title}</h4>{decision}{brief[0] if brief else ""}</div></article>')

    # Keep the scene copy, layout, and saved rehearsal cards intact.
    html = CARD.sub(render_card, html)
    extra = re.search(r'(<details id="additional" class="aux"><summary>Additional photos and continuity studies \()[0-9]+(\)</summary><div class="inside grid">)(.*?)(</div></details>)', html, re.S)
    if extra is None:
        raise ValueError("Additional photo section is missing")
    additions = []
    for identifier in sorted((files.keys() | originals.keys()) - mapped):
        source = originals.get(identifier, identifier)
        title = ("Alternate take" if ALT.fullmatch(identifier) else
                 "Study" if "study" in identifier.lower() else "Additional still")
        if source != identifier:
            title = selections[source]["original_title"]
        path = files[source]
        attribution = f'<small class="reuse">Source {source}</small>' if source != identifier else ""
        additions.append(
            f'<article class="photo-card" id="card-additional-{identifier}">'
            f'{media(path, f"{identifier} · {title}", "additional")}'
            f'<div class="card-body"><div class="card-id">{identifier}{attribution}</div><h4>{title}</h4>'
            f'{review(identifier, path, source)}</div></article>'
        )
    html = html[:extra.start()] + f'{extra[1]}{len(additions)}{extra[2]}{"".join(additions)}{extra[4]}' + html[extra.end():]

    def hero_card(match):
        caption = re.search(r'<div class="hero-cap"><span>([^<]+)</span><strong>([^<]+)</strong></div>', match[1])
        if not caption:
            return match[0]
        identifier, title = caption.groups()
        label = f"{identifier} · {unescape(title)}"
        hero = image_or_placeholder(identifier, files.get(selected.get(identifier, identifier)), label, "hero", "eager")
        return f'<article class="hero-card">{hero}{caption[0]}</article>'

    html = re.sub(r'<article class="hero-card">(.*?)</article>', hero_card, html, flags=re.S)
    versions = re.search(r'<script type="application/json" id="asset-versions">(.*?)</script>', html)
    previous = json.loads(versions[1])
    # Preserve decisions for editorial frames and saved rehearsal evidence.
    fixed = {
        identifier: digest for identifier, digest in previous.items()
        if identifier not in mapped and identifier not in previous_additions
    }
    fixed.update(fingerprints)
    html = html[:versions.start(1)] + json.dumps(fixed, sort_keys=True) + html[versions.end(1):]
    html = re.sub(r"\d+ / \d+ sequence photos available",
                  f"{len(available)} / {len(sequence)} sequence photos available", html)
    return html, available, sequence


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--local", action="store_true", help="Refresh using local files only")
    args = parser.parse_args()
    original = INDEX.read_text()
    rows = json.loads(REGISTER.read_text())
    selections = json.loads(SELECTIONS.read_text())
    if not args.local:
        ids = {CARD_ID.search(match[3])[1] for match in CARD.finditer(original)}
        ids.update(choice["use"] for choice in selections.values() if "local_file" not in choice)
        ids.update(EXTRA_SLATES)
        sync_jobs(rows, ids)
    html, available, sequence = rebuild(original, rows, selections)
    if html != original:
        local_time = datetime.now(ZoneInfo("America/Los_Angeles"))
        html = re.sub(r"Updated \d\d:\d\d [A-Z]+", f"Updated {local_time:%H:%M %Z}", html)
        write(INDEX, html)
    print(f"{len(available)} / {len(sequence)} sequence photos available")
    print("Missing sequence photos: " + (", ".join(sorted(sequence - available)) or "none"))


if __name__ == "__main__":
    main()
