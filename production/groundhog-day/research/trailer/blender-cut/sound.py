"""Conform the extended interior readings to the locked 108-second trailer.

Build from the dialogue team's original mix and four new, isolated cast pickups.
The stereo master and archive stems in audio-live stay available for the first cut.
"""
from pathlib import Path
import csv
import numpy as np
import soundfile as sf
from scipy import signal

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / 'audio-live' / 'script-mix'
RATE = 48000

def index(t):
    return round(t * RATE)

def pickup(name):
    x, sr = sf.read(HERE/'voice-pickups'/f'{name}.wav',dtype='float32'); assert sr==24000
    x = signal.resample_poly(x,2,1)
    x = signal.sosfilt(signal.butter(2,[65,15300],fs=RATE,btype='bandpass',output='sos'),x)
    voiced = np.flatnonzero(abs(x)>max(.0015,abs(x).max()*.022))
    x = x[max(0,voiced[0]-index(.022)):min(len(x),voiced[-1]+index(.047))].copy()
    # Match center-channel direct sound from the existing interior takes.
    active=x[abs(x)>.012*abs(x).max()]
    x *= min(.105/np.sqrt(np.mean(active**2)),.72/(np.max(abs(x))+1e-8))
    x[:index(.003)]*=np.linspace(0,1,index(.003));x[-index(.012):]*=np.linspace(1,0,index(.012))
    return np.stack([x,x],axis=1)

def insert(mix,start,audio):
    i=index(start); mix[i:i+len(audio)] += audio
    return start+len(audio)/RATE

def stamp(t):
    ms=round(t*1000)
    return f'{ms//3600000:02d}:{ms//60000%60:02d}:{ms//1000%60:02d},{ms%1000:03d}'

def main():
    master,sr=sf.read(SOURCE/'Trailer-mix-108s.wav',dtype='float32');assert sr==RATE
    inner,_=sf.read(SOURCE/'Stems'/'Interior voice.wav',dtype='float32')
    rows=list(csv.DictReader((SOURCE/'Script-cues.csv').open()))[:23]
    # Keep the supplied, original “I'm stuck in a loop” reading after its new lead-in.
    old=inner[index(11.66):index(12.94)].copy()
    master[index(11.56):index(13.57)]-=inner[index(11.56):index(13.57)]
    end=insert(master,12.55,old)
    rows[3]['In (seconds)']='12.55'; rows[3]['Out (seconds)']=f'{end:.3f}'
    # Start his confession as the drapes close, making room to finish before the booth.
    old=inner[index(62.35):index(67.91)].copy()
    master[index(62.35):index(67.91)]-=old
    end=insert(master,59.27,old)
    rows[12]['In (seconds)']='59.27';rows[12]['Out (seconds)']=f'{end:.3f}'
    additions=[('recognition',10.67,'That’s... the Groundhog Day situation.'),('piano',18.97,'I sit down and I play, badly, and I stay until my fingers remember a shape I do not own.'),('couch',29.46,'The couch is a couch. It does not move itself.'),('sheets',64.98,'The loop has done this to me so many times I can barely feel the texture of the sheets anymore.')]
    for name,start,line in additions:
        end=insert(master,start,pickup(name)); print(name,round(start,3),round(end,3))
        rows.append({'In (seconds)':str(start),'Out (seconds)':f'{end:.3f}','Character':'Phil','Line':line})
    for start,name in [(15.0,'01-practice'),(21.5,'02-depot-dance'),(97.0,'03-unfinished')]:
        performance,sr=sf.read(HERE/'score'/f'{name}.wav',dtype='float32');assert sr==RATE
        insert(master,start,performance)
    assert len(master)==108*RATE and np.max(abs(master))<1
    sf.write(HERE/'Trailer-complete-108s.wav',master,RATE,subtype='PCM_24')
    rows.sort(key=lambda row:float(row['In (seconds)']))
    with (HERE/'Trailer-complete.srt').open('w') as out:
        for i,row in enumerate(rows,1):
            out.write(f"{i}\n{stamp(float(row['In (seconds)']))} --> {stamp(float(row['Out (seconds)']))}\n{row['Character']}: {row['Line']}\n\n")
    print('duration',len(master)/RATE,'peak',round(np.max(abs(master)),3),'subtitle cues',len(rows))

if __name__=='__main__':main()
