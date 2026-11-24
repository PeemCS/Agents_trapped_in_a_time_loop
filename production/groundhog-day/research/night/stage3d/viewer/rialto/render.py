"""Render an offline 3D evidence cut with one authenticated source key per camera."""
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import tempfile
from playwright.sync_api import sync_playwright
from build_take import build
from verify import chrome_path

HERE=Path(__file__).resolve().parent
OUT=HERE/"evidence"
FPS=24
# Entry, lens, parallel coverage, first/last source progress, editorial screen seconds.
CUT=[
    (0,"house",False,.03,.51,2.25),
    (0,"close",False,.52,.99,2.00),
    (1,"house",True,.03,.95,4.25),
    (3,"house",False,.03,.99,3.00),
    (4,"house",False,.05,.94,3.00),
    (6,"close",False,.12,.96,2.50),
    (7,"house",True,.04,.95,4.00),
    (8,"house",False,.05,.99,5.50),
]


def main():
    take=build();OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(dir=OUT) as tmp:
        mp4=Path(tmp)/"eight-bars-3d.mp4"
        command=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","image2pipe","-framerate",str(FPS),
                 "-vcodec","mjpeg","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(mp4)]
        rows=[];frame=0
        with sync_playwright() as pw:
            browser=pw.chromium.launch(executable_path=chrome_path(),headless=True)
            page=browser.new_page(viewport={"width":960,"height":540},device_scale_factor=1)
            page.goto((HERE/"index.html").as_uri());page.wait_for_function("window.Rialto3D?.getState().renderer==='WebGL'")
            page.evaluate("Rialto3D.setCinematic(true,{captions:true})")
            encoder=subprocess.Popen(command,stdin=subprocess.PIPE)
            try:
                for i,lens,parallel,start,end,seconds in CUT:
                    source=take["shots"][i];count=round(seconds*FPS)
                    snapshot=page.evaluate("""([i,lens,twin,p])=>{Rialto3D.seek(i,p);Rialto3D.setCamera(lens);return Rialto3D.setParallel(twin)}""",[i,lens,parallel,start])
                    screens=[{"source_event_id":v["id"],"source_request_key":v["key"],"venue":v["set"]} for v in snapshot["comparison"]] if parallel else [{"source_event_id":source["id"],"source_request_key":source["key"],"venue":source["set"]}]
                    rows.append({"first_frame":frame,"frames":count,"camera":lens,"screens":screens,"source_progress":[start,end],"caption":page.locator("#cut-caption span").inner_text()})
                    for n in range(count):
                        p=start+(end-start)*n/max(1,count-1)
                        page.evaluate("a=>{Rialto3D.seek(...a);return true}",[i,p])
                        encoder.stdin.write(page.screenshot(type="jpeg",quality=91));frame+=1
                encoder.stdin.close()
                if encoder.wait()!=0:raise RuntimeError("Encoder failed")
            finally:
                if encoder.poll() is None:encoder.kill();encoder.wait()
                browser.close()
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_entries","stream=codec_name,codec_type,width,height,nb_read_frames:format=duration","-of","json",str(mp4)]))
        assert len(probe["streams"])==1 and int(probe["streams"][0]["nb_read_frames"])==frame and abs(float(probe["format"]["duration"])-frame/FPS)<.002
        manifest={"title":"Eight bars · 3D blocking cut","run":take["run"],"source":take["source"],"source_sha256":take["sha256"],
                  "file_sha256":hashlib.sha256(mp4.read_bytes()).hexdigest(),"frames":frame,"fps":FPS,"seconds":frame/FPS,
                  "renders":"Single local WebGL stage, two scissored camera viewports for paired source slots","sound":"silent",
                  "probe":probe,"shots":rows}
        ledger=Path(tmp)/"shot-ledger.json";ledger.write_text(json.dumps(manifest,indent=2,ensure_ascii=False)+"\n")
        mp4.replace(OUT/mp4.name);ledger.replace(OUT/ledger.name);print(frame,frame/FPS,str(OUT/mp4.name))


if __name__=="__main__":
    main()
