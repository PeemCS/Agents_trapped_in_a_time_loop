"""Photograph the new phone coverage and empty station on the RunPod copy of the set."""
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

def main():
    assert os.environ['RUNPOD_POD_ID']
    root=Path('stage/rialto')
    source=(root/'rialto.js').read_text()
    hook='  window.Rialto3D='
    assert source.count(hook)==1
    custom=source.replace(hook,Path('inserts.js').read_text()+'\n'+hook)
    (root/'trailer-stage.js').write_text(custom)
    index=(root/'index.html').read_text().replace('src="rialto.js"','src="trailer-stage.js"')
    (root/'trailer.html').write_text(index)
    shots=[('phone-wide',7),('phone-close',9),('phone-tight',7),('quiet-desk',10),('quiet-reels',7),('projector-detail',6),('frontdesk',7)]
    with sync_playwright() as pw:
        b=pw.chromium.launch(args=['--no-sandbox','--enable-unsafe-swiftshader','--use-gl=angle','--use-angle=swiftshader'])
        page=b.new_page(viewport={'width':1280,'height':720})
        page.goto((root/'trailer.html').resolve().as_uri())
        page.wait_for_function("window.Rialto3D?.getState().renderer==='WebGL'")
        page.evaluate('Rialto3D.setCinematic(true,{captions:false})')
        page.add_style_tag(content='#receipt,#labels,.overlay,#when,#split-name{display:none!important}')
        for name,seconds in shots:
            dest=Path('rushes')/(name+'.mp4')
            page.evaluate('n=>trailerCamera(n,.5)',name)
            page.screenshot(path=f'stills/{name}.jpg',type='jpeg',quality=90)
            with subprocess.Popen(['ffmpeg','-nostdin','-y','-loglevel','error','-f','image2pipe','-framerate','12','-vcodec','mjpeg','-i','-','-an','-c:v','libx264','-threads','3','-preset','fast','-crf','17','-pix_fmt','yuv420p',str(dest)],stdin=subprocess.PIPE) as enc:
                for i in range(seconds*12):
                    page.evaluate('([n,p])=>trailerCamera(n,p)',[name,i/(seconds*12-1)])
                    enc.stdin.write(page.screenshot(type='jpeg',quality=92))
                enc.stdin.close()
                assert enc.wait()==0
            print(name,flush=True)
        b.close()
if __name__=='__main__':main()
