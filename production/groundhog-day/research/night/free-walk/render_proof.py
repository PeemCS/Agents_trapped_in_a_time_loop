"""Render a short silent cut from actual local coordinate calls and their recorded outcomes."""
from pathlib import Path
import hashlib,json,subprocess,tempfile
from playwright.sync_api import sync_playwright
from verify_view import chrome_path
HERE=Path(__file__).resolve().parent;OUT=HERE/"evidence";FPS=24
CUT=[
    ("free",953,0,"Phil chose a point between venues",4.75,.00,1.00),
    ("free",953,2,"A second off-landmark step",2.5,.00,1.00),
    ("obstruction",967,0,"Calibration requested a point inside the hotel",3.25,.00,1.00),
    ("obstruction",967,1,"Phil receives the correction and chooses again",3.25,.00,1.00),
    ("free",913,0,"Original resolver · Two crew members reach one point",2.5,.45,1),
    ("coordinated",913,0,"Fresh model calls · Reserved crew positions",4.0,.25,1),
]
def main():
    rows=[];frame=0
    with tempfile.TemporaryDirectory() as tmp:
        clip=Path(tmp)/"free-walk.mp4"
        cmd=["ffmpeg","-y","-hide_banner","-loglevel","error","-f","image2pipe","-framerate",str(FPS),"-vcodec","mjpeg","-i","pipe:0","-an","-c:v","libx264","-preset","medium","-crf","18","-pix_fmt","yuv420p","-movflags","+faststart",str(clip)]
        encoder=subprocess.Popen(cmd,stdin=subprocess.PIPE)
        try:
            with sync_playwright() as pw:
                b=pw.chromium.launch(headless=True,executable_path=chrome_path());page=b.new_page(viewport={"width":960,"height":540},device_scale_factor=1)
                for cond,seed,turn,title,duration,start,end in CUT:
                    folder="prospective" if cond=="coordinated" else "runs";take=json.loads((HERE/folder/f"{cond}-{seed}/take.json").read_text());e=take["ticks"][turn][0]
                    page.goto((HERE/"index.html").as_uri()+f"?condition={cond}&seed={seed}");page.wait_for_function("window.FreeWalkPilot")
                    page.add_style_tag(content="header,.desk,.camera,.legend{display:none}#stage{height:100vh}#proof{position:absolute;left:20px;bottom:16px;background:#203b31ef;color:#f9efd6;padding:7px 12px;border-left:3px solid #e6bd78;font:20px Georgia,serif}#proof small{display:block;color:#ead099;font:11px ui-monospace,monospace;margin-bottom:4px}#proof p{font:13px system-ui;margin:4px 0 0}")
                    page.evaluate("""([title,e])=>{const panel=document.createElement("div");panel.id="proof";
                       const source=document.createElement("small");source.textContent="LOCAL QWEN3 0.6B   /   "+e.id;
                       const heading=document.createElement('span');heading.textContent=title;const pos=a=>'('+Number(a.x.toFixed(2))+', '+Number(a.y.toFixed(2))+')';
                       const details=document.createElement('p');details.textContent="Phil requested "+pos(e.requested)+"   →   reached "+pos(e.resolved);
                       panel.append(source,heading,details);document.querySelector('#stage').append(panel);}""",[title,e])
                    if cond=="obstruction":page.locator("#follow").evaluate("b=>b.click()")
                    count=round(duration*FPS);rows.append({"first_frame":frame,"frames":count,"title":title,"event_id":e["id"],"raw":e["raw"],"source_sha256":e["raw_sha256"],"source_progress":[start,end]})
                    for n in range(count):
                        p=start+(end-start)*n/(count-1);page.evaluate("a=>{FreeWalkPilot.seek(...a);return true}",[turn,p]);encoder.stdin.write(page.screenshot(type="jpeg",quality=90));frame+=1
                b.close()
            encoder.stdin.close();assert encoder.wait()==0
        finally:
            if encoder.poll() is None:encoder.kill();encoder.wait()
        probe=json.loads(subprocess.check_output(["ffprobe","-v","error","-count_frames","-show_entries","stream=codec_name,width,height,nb_read_frames:format=duration","-of","json",str(clip)]))
        assert int(probe["streams"][0]["nb_read_frames"])==frame and abs(float(probe["format"]["duration"])-frame/FPS)<.001
        meta={"producer":"offline isometric stage","real_model":"qwen3:0.6b","frames":frame,"seconds":frame/FPS,"fps":FPS,"sha256":hashlib.sha256(clip.read_bytes()).hexdigest(),"clips":rows,"probe":probe}
        (OUT/"movement-proof.mp4").write_bytes(clip.read_bytes());(OUT/"movement-proof.json").write_text(json.dumps(meta,indent=2)+"\n");print(frame,frame/FPS)
if __name__=="__main__":main()
