"""Assemble the 108-second picture lock, the theatrical title, and the presenter version."""
import argparse
import csv
from pathlib import Path
import subprocess
import tempfile
from PIL import Image, ImageDraw, ImageFont

HERE=Path(__file__).resolve().parent
MIX=HERE.parent/'audio-live'/'script-mix'
SIZE=(1920,824)
FPS=24

def run(*args):
    subprocess.run(['ffmpeg','-hide_banner','-loglevel','error','-y',*map(str,args)],check=True)

def end_title(file):
    w,h=SIZE
    card=Image.new('RGB',SIZE,'#0c1013')
    draw=ImageDraw.Draw(card)
    f=Path('/System/Library/Fonts/Supplemental')
    title=ImageFont.truetype(str(f/'Georgia Italic.ttf'),150)
    label=ImageFont.truetype(str(f/'Arial.ttf'),26)
    text='AGENT GROUNDHOG DAY'
    tracking=8
    widths=[draw.textlength(c,font=label) for c in text]
    x=(w-sum(widths)-(len(text)-1)*tracking)/2
    for c,width in zip(text,widths):
        draw.text((x,h*.375),c,font=label,fill='#b99b76',anchor='lm')
        x+=width+tracking
    draw.text((w*.50,h*.55),'Play It Again',font=title,fill='#f4e6d1',anchor='mm',stroke_width=0)
    card.save(file)

def assemble(picture,destination,version):
    dest=Path(destination);dest.mkdir(parents=True,exist_ok=True)
    wav=HERE/'Trailer-complete-108s.wav'
    subs=HERE/'Trailer-complete.srt'
    with tempfile.TemporaryDirectory(prefix='play-it-again-edit-') as tmp:
        tmp=Path(tmp)
        end_title(tmp/'title.png')
        coda=HERE/'voice-pickups'/'title-coda.wav'
        if coda.exists():
            end_audio=['-i',coda]
        else:
            end_audio=['-f','lavfi','-i','anullsrc=r=48000:cl=stereo']
        # The trailer plays at its authored 21:9 aspect ratio; the title follows Wednesday.
        if version!='demo':
            run('-i',picture,'-loop','1','-framerate','24','-t','3','-i',tmp/'title.png',
                '-i',wav,*end_audio,'-i',subs,
                '-filter_complex', '[0:v]setsar=1[v0];[1:v]format=yuv420p,setsar=1,fade=t=in:d=0.13,fade=t=out:st=2.75:d=0.25[v1];[v0][v1]concat=n=2:v=1:a=0[v];[3:a]aformat=sample_rates=48000:channel_layouts=stereo,apad,atrim=end=3[a1];[2:a][a1]concat=n=2:v=0:a=1[a]',
                '-map','[v]','-map','[a]','-map','4:s','-threads','6','-c:v','libx264','-preset','veryfast','-crf','16','-pix_fmt','yuv420p',
                '-c:a','aac','-b:a','256k','-c:s','mov_text','-metadata:s:s:0','language=eng',
                '-metadata','title=Play It Again','-movflags','+faststart',dest/'Play-It-Again.mp4')
        if version=='trailer':return
        # Keep the original presenter's verified 72-second picture and audio in sync.
        full_srt=(subs.read_text().rstrip()+'\n\n')
        with (MIX/'Script-cues.csv').open() as f: rows=list(csv.DictReader(f))[23:]
        def stamp(v):
            ms=round(float(v)*1000)
            return f'00:{ms//60000:02}:{ms//1000%60:02},{ms%1000:03}'
        count=len(full_srt.strip().split('\n\n'))
        for i,row in enumerate(rows,count+1):
            full_srt+=f"{i}\n{stamp(row['In (seconds)'])} --> {stamp(row['Out (seconds)'])}\nPresenter: {row['Line']}\n\n"
        (tmp/'full.srt').write_text(full_srt)
        run('-i',picture,'-i',HERE/'demo-appendix.mp4','-i',wav,'-i',tmp/'full.srt','-ss','108','-i',MIX/'Full-script-180s.wav',
            '-filter_complex','[0:v]pad=1920:1080:0:128,setsar=1[v0];[1:v]scale=1920:1080,setsar=1,setpts=PTS-STARTPTS[v1];[v0][v1]concat=n=2:v=1:a=0[v];[4:a]aresample=48000,asetpts=PTS-STARTPTS[a1];[2:a][a1]concat=n=2:v=0:a=1[a]',
            '-map','[v]','-map','[a]','-map','3:s','-t','180','-threads','6','-c:v','libx264','-preset','veryfast','-crf','17','-pix_fmt','yuv420p',
            '-c:a','aac','-b:a','256k','-c:s','mov_text','-metadata:s:s:0','language=eng','-metadata','title=Play It Again — trailer and demonstration',
            '-movflags','+faststart',dest/'Play-It-Again-with-demo.mp4')

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('picture',type=Path)
    parser.add_argument('--destination',type=Path,default=HERE)
    parser.add_argument('--version',choices=['trailer','demo','both'],default='both')
    args=parser.parse_args()
    assemble(args.picture,args.destination,args.version)
