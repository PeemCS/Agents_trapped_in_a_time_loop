"""Render an offline, receipt-linked WebGL motion proof from one authentic 27B take."""
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile

from playwright.sync_api import sync_playwright
from verify import chrome_path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parents[1] / "takes/q27/film-transcript/seed-701.json"
OUT = HERE / "evidence"
FPS = 24
# Durations and lens choices are editorial. Every action below comes from this one run.
SHOTS = [
    (5, "camera", .69, .98, 52, False),
    (6, "reporter", .04, .99, 155, True),
    (7, "reporter", .36, .99, 147, True),
    (8, "reporter", .00, .42, 72, False),
]


def main():
    raw = json.loads(SOURCE.read_text())
    OUT.mkdir(exist_ok=True)
    edit = []
    temp_dir = tempfile.TemporaryDirectory(dir=OUT)
    tmp = Path(temp_dir.name) / "motion-proof.mp4"
    command = ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-f", "image2pipe",
               "-framerate", str(FPS), "-vcodec", "mjpeg", "-i", "pipe:0", "-an", "-c:v", "libx264",
               "-preset", "medium", "-crf", "19", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)]
    with sync_playwright() as pw:
        b = pw.chromium.launch(executable_path=chrome_path(), headless=True, args=["--enable-unsafe-swiftshader"])
        pg = b.new_page(viewport={"width":960,"height":540},device_scale_factor=1)
        pg.goto((HERE/"index.html").as_uri())
        pg.wait_for_function("window.TuesdayStage3D?.getState().renderer==='WebGL'")
        pg.evaluate("r=>TuesdayStage3D.loadTrace(r)",raw)
        encoder = subprocess.Popen(command,stdin=subprocess.PIPE)
        frame = 0
        try:
            for index, role, a, z, count, captions in SHOTS:
                root=raw["events"][index]
                row=next(e for e in [root,*root["cast"]] if e["role"]==role)
                edit.append({"source_event_id":row["id"],"slot":index,"actor":row["actor"],"camera":"follow",
                    "action":row["decision"]["action"],"source_words":row["decision"]["words"],"captions":captions,
                    "source_progress":[a,z],"first_frame":frame,"frames":count})
                pg.evaluate("""arg=>{TuesdayStage3D.setCinematic(true,{captions:arg.captions});
                    TuesdayStage3D.setCamera('follow');TuesdayStage3D.follow(arg.role);}""",{"role":role,"captions":captions})
                for i in range(count):
                    p=a+(z-a)*i/max(count-1,1)
                    pg.evaluate("([i,p])=>{TuesdayStage3D.seek(i,p);return true}",[index,p])
                    encoder.stdin.write(pg.screenshot(type="jpeg",quality=91))
                    frame+=1
            encoder.stdin.close()
            if encoder.wait()!=0:raise RuntimeError("Video encoding failed")
        finally:
            if encoder.poll() is None:encoder.kill();encoder.wait()
            b.close()
    movie=OUT/"motion-proof.mp4"
    probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_entries",
        "stream=codec_name,codec_type,width,height,nb_read_frames:format=duration","-of","json",str(tmp)]))
    streams=probe["streams"]
    if len(streams)!=1 or streams[0]["codec_type"]!="video" or int(streams[0]["nb_read_frames"])!=frame:
        raise RuntimeError("The encoded movie did not pass its frame and stream check")
    if abs(float(probe["format"]["duration"])-frame/FPS)>.002:
        raise RuntimeError("The encoded movie has the wrong duration")
    meta={"take":str(SOURCE.relative_to(HERE.parents[3])),
          "source_sha256":hashlib.sha256(SOURCE.read_bytes()).hexdigest(),"film_sha256":hashlib.sha256(tmp.read_bytes()).hexdigest(),
          "source":"recorded 27B model decisions", "render":"offline browser WebGL, dressed stage", "sound":"silent",
          "encoded_stream":streams[0],"frames":frame,"fps":FPS,"size":[960,540],"duration_seconds":frame/FPS,"shots":edit}
    meta_tmp=Path(temp_dir.name)/"motion-proof.json"
    meta_tmp.write_text(json.dumps(meta,indent=2,ensure_ascii=False)+"\n")
    tmp.replace(movie);meta_tmp.replace(OUT/"motion-proof.json")
    temp_dir.cleanup()
    print(frame,frame/FPS,movie)


if __name__=="__main__":
    main()
