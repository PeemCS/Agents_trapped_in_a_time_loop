"""Drive twelve private presentation clients against one real loopback journal reader."""
import hashlib
import json
import statistics
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from tempfile import TemporaryDirectory

from director import DirectorServer, Handler
from journal import encode, records, wire
from journal_source import JournalSource

HERE = Path(__file__).resolve().parent
SLOTS = 512
VIEWERS = 12


def fixture():
    take = json.loads((HERE.parent/"takes/q27/film-receipts/seed-701.json").read_bytes())
    templates = [json.loads(line) for line in records(take)]
    header, chain = encode("begin",templates[0]["data"],"00"*32)
    originals = [t["data"]["event"] for t in templates if t["kind"]=="slot"]
    frames, lines = [], []
    for i in range(SLOTS):
        original = originals[i%len(originals)]
        frame = {**original,"id":f"load-{i}","day":i//4+1,
                 "cast":[{**e,"id":f"load-{i}-{e['role']}","day":i//4+1} for e in original["cast"]]}
        frames.append(frame)
        line, chain = encode("slot",{"offset":i,"event":frame},chain)
        lines.append(line)
    end, _ = encode("end",{"slots":len(frames)},chain)
    return header, lines, end, hashlib.sha256(wire(frames)).hexdigest()


def follow(port, viewer, started):
    if viewer >= 10:
        time.sleep(.65)
    cursor, epoch, reconnect = 0, -1, False
    frames, delays = [], []
    retries = 0
    while time.monotonic() - started < 15:
        begin = time.monotonic()
        url = f"http://127.0.0.1:{port}/api/live?epoch={epoch}&after={cursor}"
        try:
            with urllib.request.urlopen(url, timeout=4) as response:
                packet = json.load(response)
        except OSError:
            retries += 1
            time.sleep(.08)
            continue
        delays.append(1000*(time.monotonic()-begin))
        assert packet["from"] == cursor and len(packet["events"]) <= 128
        assert epoch in (-1,packet["epoch"])
        frames.extend(packet["events"])
        epoch, cursor = packet["epoch"], packet["next"]
        if packet["complete"]:
            assert cursor == SLOTS and len(frames) == SLOTS
            return {"polls":len(delays),"delays":delays,"paused":reconnect,"transport_retries":retries,
                    "late_join":viewer>=10,"digest":hashlib.sha256(wire(frames)).hexdigest()}
        if viewer in (8,9) and not reconnect and cursor >= 16:
            time.sleep(.4)
            reconnect = True
        else:
            time.sleep(.025 + viewer*.001)
    raise RuntimeError("Viewer did not catch up before timeout")


def main():
    header, lines, end, expected = fixture()
    with TemporaryDirectory() as home:
        path = Path(home)/"live.journal"
        path.write_bytes(header)
        server = DirectorServer(("127.0.0.1",0),Handler)
        server.source = JournalSource(path,0)
        thread = threading.Thread(target=server.serve_forever,daemon=True)
        thread.start()
        try:
            with ThreadPoolExecutor(max_workers=VIEWERS) as pool:
                started = time.monotonic()
                tasks = [pool.submit(follow,server.server_port,i,started) for i in range(VIEWERS)]
                with path.open("ab") as writer:
                    for start in range(0,len(lines),8):
                        writer.writelines(lines[start:start+8])
                        writer.flush()
                        time.sleep(.03)
                    writer.write(end)
                results = [task.result() for task in tasks]
            duration = time.monotonic()-started
            assert server.source.read_bytes == path.stat().st_size
            assert all(r["digest"]==expected for r in results) and sum(r["paused"] for r in results)==2
        finally:
            server.shutdown()
            server.server_close()
            thread.join(timeout=2)
    times = sorted(t for r in results for t in r["delays"])
    record = {"scope":"Local HTTP on one Apple M4 Mac. Synthetic IDs over recorded three-role presentation frames. Excludes WAN latency, GPU inference, visual frame time and authentication.",
              "viewers":VIEWERS,"slots_per_viewer":SLOTS,"actor_receipts_per_viewer":SLOTS*3,
              "late_joins":sum(r["late_join"] for r in results),"paused_resumptions":sum(r["paused"] for r in results),
              "successful_requests":len(times),"transport_retries":sum(r["transport_retries"] for r in results),
              "p50_http_ms":round(statistics.median(times),2),
              "p95_http_ms":round(times[int(.95*(len(times)-1))],2),"wall_s":round(duration,3),
              "source_bytes_read_once":server.source.read_bytes,"identical_all_viewer_sha256":expected}
    (HERE/"fanout.json").write_text(json.dumps(record,indent=2)+"\n")
    print(json.dumps(record))


if __name__ == "__main__":
    main()
