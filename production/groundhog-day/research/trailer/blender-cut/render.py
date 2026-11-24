"""Render the camera cut deterministically. Requires Chrome, Playwright and FFmpeg."""
import argparse
import base64
import functools
import http.server
import json
from pathlib import Path
import subprocess
import tempfile
import threading
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent

class QuietServer(http.server.SimpleHTTPRequestHandler):
    def log_message(self, fmt, *args):
        if args and len(args)>1 and str(args[1]).startswith('4'):
            super().log_message(fmt,*args)

def main():
    cli=argparse.ArgumentParser()
    cli.add_argument('--unit', default='all')
    cli.add_argument('--start',type=int,default=0)
    cli.add_argument('--end',type=int,default=2592)
    cli.add_argument('--width',type=int,default=1920)
    cli.add_argument('--height',type=int,default=824)
    cli.add_argument('--stills',type=Path)
    cli.add_argument('--frames',nargs='+',type=int)
    cli.add_argument('--output',type=Path)
    args=cli.parse_args()
    httpd=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(QuietServer,directory=HERE))
    threading.Thread(target=httpd.serve_forever,daemon=True).start()
    with sync_playwright() as p:
        browser=p.chromium.launch(channel='chrome',args=['--enable-gpu','--use-angle=metal','--ignore-gpu-blocklist','--disable-background-timer-throttling','--autoplay-policy=no-user-gesture-required'])
        page=browser.new_page()
        page.on('pageerror',lambda e:print('BROWSER ERROR',e,flush=True))
        page.on('console',lambda m:print('Chrome:',m.text[:1200],flush=True) if m.type in ('error','warning') else None)
        page.goto(f'http://127.0.0.1:{httpd.server_port}/stage.html?render=1&w={args.width}&h={args.height}')
        page.wait_for_function('window.ready')
        units=['hotel','exteriors','music'] if args.unit=='all' else args.unit.split(',')
        for unit in units:
            page.evaluate('name=>projection.loadUnit(name)',unit)
        shots=page.evaluate('projection.cut')
        def applicable(c):
            return c.get('root') is None or {
                'street':'exteriors','coach':'exteriors','depot':'exteriors','phone':'exteriors',
                'lobby':'hotel','bedroom':'hotel','ballroom':'music','booth':'music'
            }.get(c.get('root')) in units
        if args.stills:
            args.stills.mkdir(exist_ok=True,parents=True)
            frames=args.frames or [int((s['frame']+shots[i+1]['frame'])/2) for i,s in enumerate(shots[:-1]) if applicable(s)]
            for f in frames:
                shot=next(s for s in reversed(shots) if s['frame']<=f)
                jpg=page.evaluate("f=>{projection.paint(f);return projection.canvas.toDataURL('image/jpeg',.9).split(',')[1]}",f)
                (args.stills/f"{f:04d}-{shot['id']}.jpg").write_bytes(base64.b64decode(jpg))
        if args.output:
            temp=tempfile.TemporaryDirectory(prefix='rialto-film-')
            h264=Path(temp.name)/'frames.h264'
            with h264.open('wb') as stream:
                page.expose_function('writeVideo',lambda data: stream.write(base64.b64decode(data)))
                # WebCodecs keeps every timestamp independent of wall clock and GPU load.
                page.evaluate('''async ([start,end])=>{
                  const cfg={codec:'avc1.640033',width:projection.canvas.width,height:projection.canvas.height,bitrate:14000000,framerate:24,latencyMode:'realtime',avc:{format:'annexb'}};
                  if(!(await VideoEncoder.isConfigSupported(cfg)).supported)throw Error('H.264 encoder unavailable');
                  let chunks=[], failed;
                  const encoder=new VideoEncoder({output(c){const bytes=new Uint8Array(c.byteLength);c.copyTo(bytes);chunks.push(bytes);},error(e){failed=e.message}});
                  encoder.configure(cfg);
                  for(let f=start;f<end;f++){
                    projection.paint(f);
                    const frame=new VideoFrame(projection.canvas,{timestamp:Math.round((f-start)*1e6/24),duration:Math.round(1e6/24)});
                    encoder.encode(frame,{keyFrame:f===start||projection.cut.some(s=>s.frame===f)||(f-start)%120===0});frame.close();
                    if(encoder.encodeQueueSize>6)await new Promise(resolve=>encoder.addEventListener('dequeue',resolve,{once:true}));
                    if((f-start+1)%48===0||f===end-1){
                      await encoder.flush();
                      if(failed)throw Error(failed);
                      let buffer=[];for(const bytes of chunks){for(let pos=0;pos<bytes.length;pos+=0x6000)buffer.push(String.fromCharCode(...bytes.subarray(pos,pos+0x6000)));}
                      await window.writeVideo(btoa(buffer.join('')));chunks=[];
                    }
                  }
                  encoder.close();
                }''',[args.start,args.end])
            subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y','-fflags','+genpts','-r','24','-i',str(h264),'-c:v','copy','-movflags','+faststart',str(args.output)],check=True)
            temp.cleanup()
        browser.close()
    httpd.shutdown()
if __name__=='__main__':main()
