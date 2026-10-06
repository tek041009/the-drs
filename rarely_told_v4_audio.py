import os, urllib.request, subprocess
import numpy as np
import soundfile as sf
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
if d>29.3:
    factor=d/29.3
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={factor:.6f}","voice.wav"],check=True)
    v,_=sf.read("voice.wav",dtype="float32")
else:
    os.replace("voice_raw.wav","voice.wav")
    v,_=sf.read("voice.wav",dtype="float32")

N=sr*30
t=np.arange(N)/sr
rng=np.random.default_rng(1925)
mix=(.0065*np.sin(2*np.pi*43*t)+.0038*np.sin(2*np.pi*64.5*t)+.0022*np.sin(2*np.pi*86*t)).astype(np.float32)
mix*=.62+.38*np.sin(2*np.pi*.04*t+.8)**2
for sec in [0.05,3.85,7.75,11.65,15.5,19.4,23.3,27.15]:
    i=int(sec*sr); L=min(int(.55*sr),N-i); q=np.arange(L)/sr
    mix[i:i+L]+=.032*np.sin(2*np.pi*39*q)*np.exp(-7*q)
for sec in [3.7,7.6,11.45,15.3,19.2,23.1,27.0]:
    i=int(sec*sr); L=min(int(.36*sr),N-i); q=np.arange(L)/sr
    mix[i:i+L]+=rng.normal(0,1,L)*np.sin(np.pi*np.clip(q/.36,0,1))**2*.009
for sec in np.arange(19.8,22.5,.24):
    i=int(sec*sr); L=min(int(.018*sr),N-i)
    mix[i:i+L]+=rng.normal(0,1,L)*.007
mix[:min(N,len(v))]+=v[:N]*.96
mx=np.max(np.abs(mix))
if mx>.97: mix*=.97/mx
sf.write("mix.wav",mix,sr)
