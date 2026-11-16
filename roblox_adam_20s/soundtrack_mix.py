#!/usr/bin/env python3
"""Original royalty-free atmospheric mix under genuine Kokoro Adam narration."""
from pathlib import Path
import numpy as np
import soundfile as sf

root=Path("output")
speech,sr=sf.read(root/"adam_narration_20.wav",dtype="float32")
assert sr==24000 and len(speech)==20*sr
D=len(speech)/sr
rng=np.random.default_rng(317)
t=np.arange(len(speech),dtype=np.float64)/sr
# Low, slow, dark suspense pad and distant chimes (fully procedural original score).
score=(.023*np.sin(2*np.pi*92.5*t)+.013*np.sin(2*np.pi*138.59*t)+.009*np.sin(2*np.pi*185.0*t))
score*=.60+.18*np.sin(2*np.pi*.17*t)
score+=.007*np.sin(2*np.pi*46.25*t)*(.20+.7*t/D)
score+=.002*rng.standard_normal(len(t))
# Clock ticks; abrupt hush when time freezes.
for moment in (.30,1.07,1.84,2.61):
 i=int(moment*sr); n=min(int(.13*sr),len(t)-i); q=np.arange(n)/sr
 score[i:i+n]+=.040*np.sin(2*np.pi*1580*q)*np.exp(-q*46)
# Impacts at each story transition
for moment,vol in ((3.55,.05),(5.95,.045),(8.85,.065),(11.5,.11),(15.6,.14),(18.9,.12)):
 i=int(moment*sr);n=min(int(.75*sr),len(t)-i);q=np.arange(n)/sr
 score[i:i+n]+=vol*np.sin(2*np.pi*(78-25*q)*q)*np.exp(-q*7)
# Shadow reveal rises in pitch and strength.
p=np.clip((t-11.4)/4.2,0,1)
score+=.015*p*np.sin(2*np.pi*(124*t+20*(t-11.4).clip(0)**2))
score*=np.minimum(1,t/.24)*np.minimum(1,(D-t)/.40)
# Vocal ducking, preserving clarity.
speech_abs=np.convolve(np.abs(speech),np.ones(900)/900,mode="same")
score*=1-.63*np.clip(speech_abs/.11,0,1)
left=speech+score*1.05
right=speech+score*.88
stereo=np.stack((left,right),axis=1)
peak=np.max(np.abs(stereo))
if peak>.94: stereo*=.94/peak
sf.write(root/"adam_final_mix_20.wav",stereo,sr,subtype="PCM_16")
print("MIX_DONE",len(stereo)/sr,"seconds",sr,"Hz",float(np.sqrt(np.mean(stereo**2))))
