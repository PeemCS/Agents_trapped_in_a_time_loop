"""Finish Play It Again from the shot list, town rushes, and voice timing on RunPod."""
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import subprocess
import textwrap

import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageOps
import soundfile as sf

W, H, FPS, RATE = 1280, 720, 24, 24000
TOP, PH = 54, 545
INK = (17, 27, 28)
PAPER = (246, 235, 212)
GOLD = (229, 187, 132)
FONTS = Path('/usr/share/fonts/truetype/dejavu')
MOVIES = {'coach', 'interview', 'miss', 'reel', 'switch', 'receipt', 'phone-wide',
          'phone-close', 'phone-tight', 'quiet-desk', 'quiet-reels', 'projector-detail', 'frontdesk'}
SHEET = {'phone':('recorded-pittsburgh.png',(132,224,1280,567)),
         'hotel':('desktop-town.png',(60,147,1305,624)),
         'town':('aerial-town.png',(30,141,1332,647)),
         'projector':('stills/interview.jpg',(600,151,883,460)),
         'camera':('stills/interview.jpg',(883,86,1280,555)),
         'patch-on':('stills/switch.jpg',(546,122,1065,561))}


@lru_cache(maxsize=40)
def font(size, serif=False, bold=False):
    family='DejaVuSerif' if serif else 'DejaVuSans'
    return ImageFont.truetype(str(FONTS/(family+('-Bold' if bold else '')+'.ttf')),size)


def cover(im,progress=0):
    w,h=im.size
    ratio=W/PH
    cw,ch=(h*ratio,h) if w/h>ratio else (w,w/ratio)
    scale=1-.045*progress
    cw,ch=cw*scale,ch*scale
    cx=w*(.5+.016*progress);cy=h*.50
    return im.resize((W,PH),Image.Resampling.BICUBIC,box=(max(0,cx-cw/2),max(0,cy-ch/2),min(w,cx+cw/2),min(h,cy+ch/2)))


@lru_cache(maxsize=20)
def still(name):
    file,box=SHEET[name]
    return Image.open(file).convert('RGB').crop(box)


def title(d,x,y,phrase,size=63):
    d.text((x,y),phrase,font=font(size,serif=True),fill=PAPER,anchor='lm')


def panel(shot,p,which):
    image=Image.new('RGB',(W,PH),(22,33,34))
    d=ImageDraw.Draw(image)
    if which in ('patch','reel-detail','status','signal'):
        # Editorial insert. The metal reel and line indicator visualize the logged broadcast state.
        d.rectangle((45,65,1218,478),fill=(36,48,48),outline=(98,111,105),width=2)
        cx,cy,r=293,270,151
        d.ellipse((cx-r,cy-r,cx+r,cy+r),fill=(137,153,149),outline=(202,204,185),width=5)
        spin=(p*.44 if which in ('signal','reel-detail') else 0)
        for k in range(5):
            angle=2*math.pi*k/5+spin
            x=cx+int(math.cos(angle)*91);y=cy+int(math.sin(angle)*91)
            d.ellipse((x-38,y-38,x+38,y+38),fill=(52,62,60),outline=(181,187,170),width=3)
        d.ellipse((cx-18,cy-18,cx+18,cy+18),fill=(41,53,54))
        d.line((510,127,510,415),fill=(90,105,102),width=2)
        d.text((566,147),'REGIONAL LINE',font=font(25,bold=True),fill=GOLD)
        if which=='reel-detail': main,sub="Alma’s interview","RIALTO PROJECTION BOOTH"
        elif which=='signal': main,sub="Pittsburgh","INTERVIEW RECEIVED"
        elif which=='status': main,sub=shot['card'],"NO TRANSMISSION"
        else: main,sub="Alma’s interview","RECORDING AVAILABLE"
        title(d,566,268,main,44)
        d.ellipse((568,351,583,366),fill=(135,213,169) if which=='signal' else (137,135,114))
        d.text((604,341),sub,font=font(20),fill=PAPER)
    elif which=='edit':
        for i,asset in enumerate(('piano','miss','interview')):
            frame=Image.open('stills/'+asset+'.jpg')
            frame=ImageOps.fit(frame,(372,218),method=Image.Resampling.LANCZOS)
            image.paste(frame,(56+i*397,50))
        title(d,57,380,shot['card'],58)
    else:
        d.text((W//2,170),'AGENT GROUNDHOG DAY',font=font(22,bold=True),fill=GOLD,anchor='mm')
        d.text((W//2,280),shot['card'],font=font(102,serif=True),fill=PAPER,anchor='mm')
    return image


def words(d,cue):
    face=font(30)
    lines=[]
    line=''
    for word in cue['line'].split():
        candidate=(line+' '+word).strip()
        if line and d.textlength(candidate,font=face)>960:
            lines.append(line);line=word
        else:line=candidate
    lines.append(line)
    if len(lines)>2: raise ValueError(cue)
    d.text((47,648),cue['voice'].upper(),font=font(18,bold=True),fill=GOLD,anchor='lm')
    y=650 if len(lines)==1 else 630
    for line in lines:
        d.text((204,y),line,font=face,fill=PAPER,anchor='lm');y+=40


def draw_shot(encoder,shot,number,cues):
    name=shot['visual'];frames=shot['seconds']*FPS; decoder=None
    if name in MOVIES:
        decoder=subprocess.Popen(['ffmpeg','-nostdin','-loglevel','error','-i',f'rushes/{name}.mp4','-an',
            '-vf',f'fps={FPS},tpad=stop_mode=clone:stop_duration=5,crop=1280:{PH-1}:0:66,scale=1280:{PH}',
            '-frames:v',str(frames),'-f','rawvideo','-pix_fmt','rgb24','pipe:1'],stdout=subprocess.PIPE)
    try:
        for i in range(frames):
            p=i/max(1,frames-1)
            if decoder:
                buf=decoder.stdout.read(W*PH*3)
                if len(buf)!=W*PH*3:raise RuntimeError(f'Missing frame {number}/{i}')
                img=Image.frombytes('RGB',(W,PH),buf)
            elif name in SHEET:
                img=cover(still(name),p)
            else:img=panel(shot,p,name)
            if name in ('hotel', 'frontdesk'):
                img=Image.blend(img,Image.new('RGB',img.size,INK),.46)
                title(ImageDraw.Draw(img),66,445,shot['card'] or 'Tuesday, February 2',58)
            out=Image.new('RGB',(W,H),INK);out.paste(img,(0,TOP));d=ImageDraw.Draw(out)
            d.text((45,27),shot['slate'],font=font(19,bold=True),fill=GOLD,anchor='lm')
            if shot['slate']:d.text((1236,27),'MILL CREEK, PA' if name=='town' else 'PLAY IT AGAIN',font=font(17),fill=(171,185,177),anchor='rm')
            at=shot['at']+i/FPS
            active=next((c for c in cues if c['start']-.03<=at<c['end']+.035),None)
            if active:words(d,active)
            encoder.stdin.write(out.tobytes())
    finally:
        if decoder:
            decoder.stdout.close()
            if decoder.wait()!=0:raise RuntimeError('Source decode failed')


def soundtrack(edit):
    voice,rate=sf.read('dialogue.wav',dtype='float32')
    assert rate==RATE
    bed=np.zeros_like(voice)
    rng=np.random.default_rng(841)
    def note(at,pitch,duration,vol):
        n=round(duration*RATE);t=np.arange(n)/RATE
        env=np.minimum(1,t/.014)*np.exp(-3.7*t/duration)*np.minimum(1,(duration-t)/.06)
        wave=(np.sin(2*np.pi*pitch*t)+.28*np.sin(2*np.pi*pitch*2.002*t)+.09*np.sin(2*np.pi*pitch*3*t))*env*vol
        off=round(at*RATE);size=min(n,len(bed)-off)
        if size>0:bed[off:off+size]+=wave[:size]
    def sound(at,duration,vol):
        n=round(duration*RATE);t=np.arange(n)/RATE
        off=round(at*RATE)
        bed[off:off+n]+=rng.normal(0,vol,n)*np.exp(-t*6/duration)*np.minimum(1,t/.005)
    for i,s in enumerate(edit):
        at=s['at'];name=s['visual']
        if name in ('hotel', 'frontdesk'):
            for dt,f in zip((0,.23,.49),(523.25,659.25,587.33)):note(at+dt,f,.42,.085)
        if name.startswith('phone'):
            note(at+.02,440,.14,.08);note(at+.02,480,.14,.05);sound(at+.17,.09,.06)
        if name in ('interview','camera','projector','projector-detail'):
            for dt in np.arange(0,s['seconds']-.06,.12):sound(at+dt,.035,.012)
        if name in ('signal','switch','reel'):sound(at+.16,.12,.09)
        if name in ('receipt','end'):continue
        if name=='status':continue
        for j in range(0,s['seconds']-1,3):
            tone=(146.83,174.61,220.00,261.63,196.0)[(i+j//3)%5]
            note(at+j+.35,tone,2.4,.031)
            if name in ('miss','edit','coach'):note(at+j+1.25,tone*1.5,1.45,.025)
    mix=voice+bed
    peak=max(.01,np.max(np.abs(mix)))
    sf.write('mix.wav',mix*min(1,.92/peak),RATE)


def srt_time(t):
    ms=round(t*1000)
    return f'{ms//3600000:02}:{ms//60000%60:02}:{ms//1000%60:02},{ms%1000:03}'


def main():
    if not os.getenv('RUNPOD_POD_ID'):raise SystemExit('Run the film render on RunPod.')
    edit=json.loads(Path('cut.json').read_text());cues=json.loads(Path('timing.json').read_text())
    clock=0
    for s in edit:s['at']=clock;clock+=s['seconds']
    assert clock==180
    soundtrack(edit)
    encoder=subprocess.Popen(['ffmpeg','-y','-nostdin','-loglevel','error','-f','rawvideo','-pix_fmt','rgb24',
        '-s','1280x720','-r',str(FPS),'-i','-','-i','mix.wav','-map','0:v','-map','1:a','-c:v','libx264',
        '-threads','6','-preset','fast','-crf','18','-pix_fmt','yuv420p','-af','volume=1.52,alimiter=limit=0.85:level=0:latency=1','-c:a','aac','-b:a','160k',
        '-movflags','+faststart','Play-It-Again.mp4'],stdin=subprocess.PIPE)
    try:
        for i,shot in enumerate(edit):
            draw_shot(encoder,shot,i,[c for c in cues if c['shot']==i])
            print(i+1,shot['visual'],flush=True)
        encoder.stdin.close()
        if encoder.wait()!=0:raise RuntimeError('Film encoding failed')
    finally:
        if encoder.poll() is None:encoder.kill();encoder.wait()
    cc=sorted(cues+[{'start':s['at']+.2,'end':s['at']+s['seconds']-.2,'voice':'Written reply',
                     'line':'I know that voice. Play it again.'} for s in edit if s['visual']=='receipt'],key=lambda c:c['start'])
    Path('Play-It-Again.srt').write_text('\n\n'.join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['voice']}: {c['line']}" for i,c in enumerate(cc,1))+'\n')


if __name__=='__main__':
    main()
