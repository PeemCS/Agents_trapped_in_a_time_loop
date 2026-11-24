"""Render the 72-second, picture-only S07 native evidence feed at 24 fps."""
import io
import json
import math
import subprocess
import tempfile
from functools import lru_cache
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE=Path(__file__).resolve().parent
TRAILER=HERE.parent
RUNS=TRAILER.parent/'night'
CAP=TRAILER/'storyboard/units/S07-captures'
STAGE=RUNS/'stage3d/viewer/rialto/evidence'
SQL=RUNS/'editor/bruin/pipeline/assets/coach_payoffs.sql'
FONTS=Path('/System/Library/Fonts/Supplemental')
INK='#f0ece2'; SUB='#bec8c1'; DARK='#101c20'; SHEET='#1a2b30'; RULE='#425456'; MINT='#a7d6b8'; GOLD='#eac99a'
W,H=1920,1080

@lru_cache(None)
def font(family,size):
    name={'display':'Georgia.ttf','italic':'Georgia Italic.ttf','sans':'Arial.ttf','bold':'Arial Bold.ttf','mono':'Courier New.ttf','mb':'Courier New Bold.ttf'}[family]
    return ImageFont.truetype(str(FONTS/name),size)

def txt(draw,x,y,words,size=32,color=INK,face='sans'):
    draw.text((x,y),words,font=font(face,size),fill=color,anchor='lt')

def fit(draw,x,y,words,limit,size=32,color=INK,face='sans'):
    while draw.textlength(words,font=font(face,size))>limit and size>16:size-=1
    txt(draw,x,y,words,size,color,face)

def rule(draw,x1,y,x2):draw.line((x1,y,x2,y),fill=RULE,width=2)

def shell(section,title,source):
    img=Image.new('RGB',(W,H),DARK);d=ImageDraw.Draw(img)
    txt(d,96,58,'GROUNDHOG DAY',25,MINT,'bold');txt(d,357,60,'/   REHEARSAL ROOM',23,SUB,'mono')
    f=font('mono',23);wide=d.textlength(section,font=f);txt(d,1824-wide,60,section,23,GOLD,'mono')
    rule(d,96,112,1824);txt(d,96,143,title,68,INK,'display')
    rule(d,96,969,1824);fit(d,96,992,source,1718,24,SUB,'mono');return img,d

def mount(img,raw,x,y,w,h,mode='contain'):
    raw=raw.convert('RGB')
    if mode=='cover': pic=ImageOps.fit(raw,(w,h),method=Image.Resampling.LANCZOS)
    else:
        pic=ImageOps.contain(raw,(w,h),method=Image.Resampling.LANCZOS)
        x+=(w-pic.width)//2;y+=(h-pic.height)//2
    img.paste(pic,(x,y))

def snap(name):return Image.open(CAP/name).convert('RGB')

def stage():return Image.open(STAGE/'parallel-evening.png').convert('RGB')

def flow_diagram():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        browser=pw.chromium.launch(channel='chrome',headless=True);p=browser.new_page(viewport={'width':1260,'height':540},device_scale_factor=1.5)
        p.goto((TRAILER/'storyboard/sets/S07-stack.svg').as_uri());png=p.screenshot();browser.close()
    return Image.open(io.BytesIO(png)).convert('RGB')

def two_rooms():
    im,d=shell('RECORDED PERFORMANCE','Two rooms, one evening.','Rialto 721  /  Tuesday 1  /  supplied movie theory  /  recorded stage replay')
    # Preserve both rooms and the actual caption. Crop only the viewer toolbar.
    a=stage();a=a.crop((0,57,1365,774));mount(im,a,96,244,1728,691)
    return im

def action(evening):
    title='Where he actually went.' if evening else 'What Phil meant to do.'
    im,d=shell('ACTOR MONITOR',title,'Rialto 721-hypothesis  /  Tuesday 1  /  '+('d01-t01-reporter' if evening else 'd01-t00-reporter'))
    txt(d,98,264,'COMMITTED EVENING ACTION' if evening else 'RECORDED STATED INTENTION',25,GOLD,'mono')
    txt(d,98,337,'“Sit at depot.”' if evening else '“Test the theory. Not the coach.',57,INK,'display')
    if not evening:txt(d,98,413,'Not the couch. The piano.”',57,INK,'display')
    else:txt(d,98,430,'Phil sits on the empty depot bench.',37,SUB,'sans')
    pic=snap('721-depot.png' if evening else '721-piano.png');mount(im,pic,98,519,1724,400);return im

def witnesses(proposed=False):
    ev=json.loads((CAP/'policy-209-events.json').read_text());a,b=ev['events'];im,d=shell('LOCAL-POLICY REHEARSAL','Who witnessed the sale?',f"Peem’s policy-209  /  world seed {ev['world_seed']}  /  policy seed {ev['policy_seed']}  /  source SHA-256 {ev['source_sha256'][:16]}…")
    for yy,obj,field in [(270,a,a['action']),(500,b,b['type'])]:
        d.rounded_rectangle((96,yy,1824,yy+188),16,fill=SHEET,outline=RULE,width=2)
        txt(d,132,yy+32,obj['id'],40,MINT,'mb');txt(d,416,yy+35,field,45,INK,'mono')
        txt(d,134,yy+108,'07:30    main_st    loop 2',26,SUB,'mono')
        if 'witnesses' in obj:txt(d,739,yy+111,'"witnesses": '+json.dumps(obj['witnesses']),35,GOLD,'mb')
    if proposed:
        txt(d,98,762,'PROPOSED SCENE',25,GOLD,'mono');txt(d,98,813,'Ned tells Rita he waited. On Wednesday, she remembers the two bars.',38,INK,'display')
    return im

def diagram(native,later):
    im,d=shell('ROOM ACTIONS AND WITNESSES','What can Rita learn?', 'S07-stack.svg  /  Band adapter at 92ee87d  /  direct Ned-to-Rita receipt proposed')
    pic=native.copy()
    if not later:
        pd=ImageDraw.Draw(pic);pd.rectangle((0,round(pic.height*.613),pic.width,pic.height),fill='#17232a')
    mount(im,pic,96,228,1728,714)
    return im

def payoff(done):
    rec=json.loads((RUNS/'editor/matched-film-bruin.json').read_text());row=rec['coach']['rows'][0];sql=SQL.read_text();condition='arrival_slot < city_slot AND city_slot < wake_slot';assert condition in sql
    im,d=shell('BRUIN / DUCKDB','Three events make a coach trip.','town.coach_payoffs  /  coach_payoffs.sql  /  matched-film-bruin.json')
    for i,(label,key,val,sid) in enumerate([('Arrive in Pittsburgh','arrival_slot',row[2],row[1]),('Remain in the city','city_slot',row[4],row[3]),('Wake at the inn','wake_slot',row[6],row[5])]):
        x=96+i*582;d.rounded_rectangle((x,276,x+560,553),15,fill=SHEET,outline=RULE,width=2)
        txt(d,x+29,309,label,34,INK,'display');txt(d,x+29,382,key,26,SUB,'mono');txt(d,x+29,443,str(val),67,MINT,'mb');txt(d,x+141,473,sid,24,SUB,'mono')
    txt(d,98,622,'ORDERED CHECK',25,GOLD,'mono');txt(d,98,677,condition,43,INK,'mono')
    if done:
        assert 'PASS town.coach_payoffs' in rec['run_log']
        d.rounded_rectangle((96,790,1824,893),14,fill='#263f38');txt(d,131,824,'PASS  town.coach_payoffs',37,MINT,'mb');txt(d,1017,829,'2 assets succeeded  /  3 quality checks succeeded',24,INK,'mono')
    return im

def replay(choice):
    meta={'recorded':('Recorded performance','The recorded evening.'),'dance':('Alternate choices · rule replay','Give Phil the dance.'),'wire':('Alternate choices · rule replay','Give Rita the regional line.')}
    status,title=meta[choice];im,d=shell('WRITER’S SWITCHBOARD',title,'Rialto 721-hypothesis  /  Tuesday 1  /  recorded afternoon held fixed')
    txt(d,98,276,status.upper(),28,MINT if choice=='recorded' else GOLD,'mono')
    pic=snap('721-'+choice+'-consequences.png');mount(im,pic,98,360,1724,260)
    if choice=='wire':
        txt(d,98,701,'Always reset',30,SUB,'sans');txt(d,98,775,'Tuesday',64,INK,'display')
        txt(d,970,701,'Release on delivery',30,SUB,'sans');txt(d,970,775,'Wednesday',64,GOLD,'display')
    elif choice=='dance':
        txt(d,98,701,'Always reset',30,SUB,'sans');txt(d,98,775,'Tuesday',64,INK,'display')
        txt(d,970,701,'Release on delivery',30,SUB,'sans');txt(d,970,775,'Tuesday',64,INK,'display')
    else:
        txt(d,98,741,'Phil sits at the depot. Rita goes to the ballroom.',45,INK,'display')
    return im

def question():
    im,d=shell('PROPOSED SCENE','The next take.','Recorded evening restored  /  Rialto 721-hypothesis  /  Tuesday 1')
    src=stage().crop((0,75,1365,580));mount(im,src,96,258,1728,645,'cover')
    overlay=Image.new('RGBA',(1728,645),(8,15,17,186));im.paste(overlay,(96,258),overlay);d=ImageDraw.Draw(im)
    txt(d,165,418,'PROPOSED SCENE',26,GOLD,'mono');txt(d,160,500,'What does Rita choose',88,INK,'display');txt(d,160,620,'after Ned tells her?',88,INK,'display');return im

def jpg(im):
    b=io.BytesIO();im.save(b,'JPEG',quality=94,subsampling=0);return b.getvalue()

def main():
    native=flow_diagram()
    # Times are relative to the start of the presenter track at 01:48.
    screens=[(0,two_rooms()),(6,action(False)),(10,action(True)),(14,witnesses()),(19.6,witnesses(True)),(22,witnesses(False)),(23.4,diagram(native,False)),(29,diagram(native,True)),(34,payoff(False)),(40.6,payoff(True)),(47,replay('recorded')),(48.45,replay('dance')),(56,replay('wire')),(64,replay('recorded')),(65.35,question())]
    fps=24
    arguments=['ffmpeg','-hide_banner','-loglevel','error','-y','-f','image2pipe','-framerate',str(fps),'-c:v','mjpeg','-i','-','-an','-c:v','libx264','-threads','4','-preset','veryfast','-tune','stillimage','-crf','16','-pix_fmt','yuv420p','-movflags','+faststart',str(HERE/'demo-appendix.mp4')]
    with subprocess.Popen(arguments,stdin=subprocess.PIPE) as proc:
        for i,(start,screen) in enumerate(screens):
            begin=round(start*fps);end=round(screens[i+1][0]*fps) if i+1<len(screens) else 72*fps
            transition=5 if i else 0;still=jpg(screen)
            for f in range(end-begin):
                packet=jpg(Image.blend(screens[i-1][1],screen,(f+1)/(transition+1))) if f<transition else still
                proc.stdin.write(packet)
        proc.stdin.close()
        if proc.wait():raise RuntimeError('FFmpeg could not encode appendix')
    print('S07 digital feed  /  1,728 frames  /  72.000 seconds')

if __name__=='__main__':main()
