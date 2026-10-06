import os, urllib.request, subprocess
import numpy as np, soundfile as sf
from kokoro_onnx import Kokoro

def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
if not os.path.exists(model): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices): dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=("In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
        "His name was Victor Lustig, and he had a talent for making impossible lies sound completely reasonable. "
        "Then, one morning in Paris, he noticed a newspaper story complaining about how expensive the Eiffel Tower was becoming to maintain. "
        "Most people would have read it and moved on. Lustig saw something else: an opportunity.")

k=Kokoro(model,voices)
v,sr=k.create(script,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice_raw.wav",v,sr)
d=len(v)/sr
if d>29.25:
    f=d/29.25
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={f:.6f}","voice.wav"],check=True)
    v,_=sf.read("voice.wav",dtype="float32")
else:
    os.replace("voice_raw.wav","voice.wav"); v,_=sf.read("voice.wav",dtype="float32")

N=sr*30; t=np.arange(N)/sr; rng=np.random.default_rng(71)
# cinematic underscore: low strings + restrained pulse
mix=(.007*np.sin(2*np.pi*43*t)+.004*np.sin(2*np.pi*64.5*t)+.0025*np.sin(2*np.pi*86*t)).astype(np.float32)
mix*=.6+.4*np.sin(2*np.pi*.04*t+.8)**2
for sec in [0.05,4.5,7.0,16.6,20.8,26.0]:
    i=int(sec*sr); L=min(int(.7*sr),N-i); q=np.arange(L)/sr
    mix[i:i+L]+=.05*np.sin(2*np.pi*39*q)*np.exp(-6*q)
for sec in [6.8,16.4,20.5,25.8]:
    i=int(sec*sr); L=min(int(.42*sr),N-i); q=np.arange(L)/sr
    mix[i:i+L]+=rng.normal(0,1,L)*np.sin(np.pi*np.clip(q/.42,0,1))**2*.012
# paper flicks / type ticks
for sec in np.arange(21.5,24.3,.24):
    i=int(sec*sr); L=min(int(.018*sr),N-i); mix[i:i+L]+=rng.normal(0,1,L)*.011
mix[:min(N,len(v))]+=v[:N]*.96
mx=np.max(np.abs(mix))
if mx>.97: mix*=.97/mx
sf.write("mix.wav",mix,sr)
