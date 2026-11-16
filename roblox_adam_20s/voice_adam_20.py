#!/usr/bin/env python3
"""Genuine Kokoro ONNX Adam (am_adam) for 20-second 3:17 AM story. No paid API."""
from pathlib import Path
import urllib.request,hashlib,json,subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

OUT=Path("output"); OUT.mkdir(exist_ok=True)
ROOT=Path("model_cache"); ROOT.mkdir(exist_ok=True)
URL="https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/"
assets={"kokoro-v1.0.int8.onnx":70_000_000,"voices-v1.0.bin":25_000_000}
for f,minimum in assets.items():
 p=ROOT/f
 if not p.exists() or p.stat().st_size<minimum:
  print("Downloading authentic Kokoro asset",f,flush=True)
  req=urllib.request.Request(URL+f,headers={"User-Agent":"RobloxViralStory/1.0"})
  with urllib.request.urlopen(req,timeout=120) as response,p.open("wb") as target:
   while data:=response.read(1024*1024):target.write(data)
 assert p.stat().st_size>=minimum,(f,p.stat().st_size)
 print("verified size",f,p.stat().st_size,flush=True)
voice=Kokoro(str(ROOT/"kokoro-v1.0.int8.onnx"),str(ROOT/"voices-v1.0.bin"))
SR=24000;D=20;master=np.zeros(SR*D,dtype=np.float32)
segments=[
 (0.13,3.55,"At three seventeen, our entire town froze."),
 (3.70,5.95,"Everyone... except me."),
 (6.04,8.85,"Then I saw someone else moving."),
 (8.94,11.50,"She pointed at the street."),
 (11.60,15.60,"My shadow was walking away... without me."),
 (15.75,19.95,"Then it turned around... and waved.")
]
manifest={"voice":"am_adam","engine":"kokoro-onnx","genuine":True,"segments":[]}
for i,(st,end,txt) in enumerate(segments):
 print("Synth",i,txt,flush=True)
 arr,sr=voice.create(txt,voice="am_adam",speed=1.04,lang="en-us")
 arr=np.asarray(arr,dtype=np.float32).reshape(-1)
 assert sr==SR,(sr,SR)
 assert np.isfinite(arr).all() and np.sqrt(np.mean(arr*arr))>0.001,(i,"silence")
 slot=int((end-st-0.10)*SR)
 if len(arr)>slot:
  sf.write(OUT/f"temp_{i}.wav",arr,SR)
  factor=len(arr)/slot
  subprocess.run(["ffmpeg","-y","-loglevel","error","-i",str(OUT/f"temp_{i}.wav"),"-filter:a",f"atempo={factor:.5f}","-ar",str(SR),str(OUT/f"fitted_{i}.wav")],check=True)
  arr,sr=sf.read(OUT/f"fitted_{i}.wav",dtype="float32")
  arr=np.asarray(arr,dtype=np.float32).reshape(-1)
  (OUT/f"temp_{i}.wav").unlink(); (OUT/f"fitted_{i}.wav").unlink()
  print("fitted",i,"factor",factor,flush=True)
 n=min(len(arr),slot); arr=arr[:n]
 if n>250:
  r=min(300,n//4)
  arr[:r]*=np.linspace(0,1,r)
  arr[-r:]*=np.linspace(1,0,r)
 master[int(st*SR):int(st*SR)+n]+=arr*.90
 sf.write(OUT/f"adam_line_{i}.wav",arr,SR)
 manifest["segments"].append({"index":i,"text":txt,"voice":"am_adam","start":st,"end":round(st+n/SR,3),"samples":n})
print("Narration peak",float(abs(master).max()),"rms",float(np.sqrt(np.mean(master**2))),flush=True)
assert np.sqrt(np.mean(master**2))>0.018
sf.write(OUT/"adam_narration_20.wav",master,SR)
manifest["asset_sha256"]={f:hashlib.sha256((ROOT/f).read_bytes()).hexdigest() for f in assets}
manifest["narration_sha256"]=hashlib.sha256((OUT/"adam_narration_20.wav").read_bytes()).hexdigest()
(OUT/"manifest.json").write_text(json.dumps(manifest,indent=2))
