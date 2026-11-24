"""Perform an original practice phrase and its unfinished reprise on the shot clock.

The native Logic Steinway instrument is used as a source on this Mac. The four
rendered stereo cues are portable with the reconstruction and can be remixed.
"""
import json
import math
import struct
from pathlib import Path
import numpy as np
from scipy import signal
import soundfile as sf

HERE=Path(__file__).resolve().parent
CUES=HERE/'score'; CUES.mkdir(exist_ok=True)
MAP=json.loads((HERE/'piano-score.json').read_text())
LIBRARY=Path('/Library/Application Support/Logic')
PATCH=LIBRARY/'Sampler Instruments/01 Acoustic Pianos/Steinway Grand Piano 2.exs'
PCM=LIBRARY/'EXS Factory Samples/01 Acoustic Pianos/Steinway Piano_consolidated.caf'
SR=48000

def zones():
    # EXS24 v2 holds region metadata separately from consolidated stereo samples.
    raw=PATCH.read_bytes();pos=0;regions=[]
    while pos+84<=len(raw):
        kind=raw[pos+3];size=struct.unpack_from('<I',raw,pos+4)[0]
        block=raw[pos+84:pos+84+size]
        if kind==0x41:
            key,lo,hi=block[1],block[6],block[7]
            start,end=struct.unpack_from('<2I',block,12)
            if len(regions)<30:regions.append((key,lo,hi,start,end))
        pos+=84+size
    return regions

REGIONS=zones()

def played_note(midi,hold,velocity):
    key,_,_,start,end=next(z for z in REGIONS if z[1]<=midi<=z[2]);
    with sf.SoundFile(PCM) as f:
        f.seek(start);x=f.read(end-start,dtype='float32');file_rate=f.samplerate
    # Sustain phase, sympathetic tail and the damped string after release.
    length=hold+.50;ratio=2**((midi-key)/12)*file_rate/SR
    t=np.arange(round(length*SR))/SR
    ii=np.arange(len(t))*ratio
    wave=np.stack([np.interp(ii,np.arange(len(x)),x[:,c]) for c in range(2)],axis=1)
    wave=signal.sosfilt(signal.butter(2,2700+velocity*1150,fs=SR,output='sos'),wave,axis=0)
    wave*=np.minimum(1,t/.004)[:,None]*np.exp(-np.maximum(0,t-hold)*8)[:,None]
    wave*=velocity/max(1e-8,np.max(abs(wave)))
    return wave.astype('float32')

def add(buf,t,wave):
    begin=round(SR*t);use=min(len(wave),len(buf)-begin)
    if use>0:buf[begin:begin+use]+=wave[:use]

def room(x,wet=.2):
    y=x.copy()
    for delay,gain,pan in [(.021,.38,.78),(.037,.28,.34),(.058,.19,.85),(.092,.14,.26),(.133,.10,.72),(.193,.08,.24),(.278,.055,.50),(.39,.04,.80)]:
        k=round(SR*delay);y[k:]+=x[:-k,::-1]*wet*gain*np.array([pan,1-pan])*2
    return y

def out(path,x):
    fade=min(round(.045*SR),len(x));x[-fade:]*=np.linspace(1,0,fade)[:,None]
    sf.write(path,x,SR,subtype='PCM_24')

def melodic(section,duration,rate):
    result=np.zeros((round(SR*duration),2),dtype='float32');notes=MAP[section]
    for j,finger in enumerate(notes):
        # Sound the hammer as the animated key first starts down.
        when=j/rate+.053
        hold=(.19 if section=='practice' else .36) if j+1<len(notes) else (duration-when-.14)
        vel=([.77,.53,.68,.65,.75,.45,.54,.77,.53,.68,.65,.73,.65,.52,.48,.65,.55][j] if section=='practice' else [.71,.49,.60,.63,.70,.56,.55,.49,.48][j])
        add(result,when,played_note(MAP['fingerNotes'][finger],hold,vel))
    # The practiced shape ends on a quiet open interval. At night, only the
    # suspended C remains, leaving the F resolution for the title card.
    if section=='practice':
        add(result,5.48,played_note(53,.78,.25));add(result,5.51,played_note(57,.72,.18))
    return room(result,wet=.28)*(.187 if section=='practice' else .16)

def dance():
    length=6; result=np.zeros((SR*length,2),dtype='float32');rng=np.random.default_rng(321);beat=.51
    for bar,(root,chord) in enumerate([(46,[53,58,62]),(43,[55,59,62]),(48,[55,60,64]),(41,[53,57,60])]):
        for b in range(3):
            start=(bar*3+b)*beat
            if start>=length:continue
            if b==0:
                add(result,start,played_note(root,.38,.38));
            else:
                for n in chord:add(result,start+.006*(n%3),played_note(n,.15,.115))
            # The brush on two and three leaks through the ballroom door.
            t=np.arange(round(.25*SR))/SR
            brush=signal.sosfilt(signal.butter(2,[700,4400],fs=SR,btype='bandpass',output='sos'),rng.normal(0,.14,len(t)))*np.exp(-t*26)
            add(result,start,np.stack([brush*.81,brush],axis=1)*.25)
    result=room(result,.93)
    result=signal.sosfilt(signal.butter(4,[135,1050],fs=SR,btype='bandpass',output='sos'),result,axis=0)
    n=len(result);result*=np.minimum(1,np.arange(n)/(SR*.24))[:,None]*np.minimum(1,np.arange(n)[::-1]/(SR*.36))[:,None]
    return result*.102

def coda():
    result=np.zeros((SR*3,2),dtype='float32')
    for t,n,h,v in [(.03,60,.98,.37),(.57,57,1.54,.42),(.60,53,1.70,.53),(.63,65,1.49,.22)]:
        add(result,t,played_note(n,h,v))
    result=room(result,.48)*.22
    result[-round(SR*.45):]*=np.linspace(1,0,round(SR*.45))[:,None]
    return result

if __name__=='__main__':
    out(CUES/'01-practice.wav',melodic('practice',6.5,3));out(CUES/'02-depot-dance.wav',dance())
    out(CUES/'03-unfinished.wav',melodic('reprise',6,2));out(HERE/'voice-pickups'/'title-coda.wav',coda())
