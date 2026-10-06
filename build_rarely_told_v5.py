import os, shutil, subprocess, time, urllib.request
from gradio_client import Client, handle_file
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

T2V_SPACE="ChopperBlu/ltx-2-5-demo"
MSR_SPACE="hugging-apps/ltx25-multi-subject-reference"
t2v=Client(T2V_SPACE)
msr=Client(MSR_SPACE)

STYLE=(
"Current-generation 2026 cinematic stylized 3D animation with feature-film polish, realistic human proportions, "
"stable anatomy, refined expressive facial animation, rich skin and cloth materials, physically believable motion and weight, "
"coherent geometry, warm 1920s Paris palette, soft global illumination, volumetric atmosphere, cinematic depth of field, "
"natural secondary motion, premium art direction, no text, no watermark, no dialogue, only subtle natural ambient sound. "
)
VICTOR=(
"Victor Lustig is the same recurring character in every shot: a handsome European man in his late thirties, slim build, "
"narrow oval face, neat dark pencil moustache, dark brown hair under a charcoal fedora, tailored charcoal 1920s three-piece suit, "
"cream shirt, muted gold tie, polished black shoes. "
)

PROMPTS={
1: STYLE+(
"Wide establishing shot of Paris in 1925 at golden hour. The Eiffel Tower dominates the skyline beyond a lively boulevard. "
"Authentic 1920s cars roll through traffic, pedestrians cross naturally, cafe awnings ripple slightly in the breeze, warm sun glints on wet stone. "
"The camera performs a smooth slow crane-and-dolly forward toward the tower. Grand, intriguing, grounded, richly detailed."
),
2: STYLE+VICTOR+(
"He walks confidently toward camera down a bustling Paris boulevard. Period cars pass behind him, pedestrians weave naturally around him, "
"his coat hem and tie move with the breeze. The Eiffel Tower is softly visible in the distant haze. "
"Smooth chest-height tracking camera moving backward with him; nuanced expression, subtle confidence."
),
3: STYLE+VICTOR+(
"Medium close tracking shot from three-quarter profile as Victor moves through an upscale Paris crowd. "
"He gives a faint knowing smile, studies the people around him, then adjusts one cuff with practiced confidence. "
"Elegant hotel facades and warm shop windows slide by in deep parallax. Smooth lateral dolly and stable face."
),
4: STYLE+VICTOR+(
"Inside an opulent 1920s Paris hotel lounge, Victor calmly charms two wealthy businessmen in tailored suits. "
"He speaks with relaxed confidence using measured hand gestures while they listen closely, then gives a tiny knowing smile. "
"Marble, brass, art deco lamps and polished floors; background guests move naturally. Slow elegant circular camera move around the group."
),
5: STYLE+VICTOR+(
"Morning in an elegant Paris cafe beside a large rain-streaked window. Victor sits alone at a small table with an espresso. "
"A waiter enters frame and places a folded French newspaper onto the table. Victor reaches for it naturally. "
"Outside, pedestrians and 1920s cars move through soft morning rain. Intimate cinematic dolly-in."
),
6: STYLE+VICTOR+(
"Close cinematic shot at Victor's cafe table. He unfolds a large 1920s French newspaper and scans the page. "
"His finger pauses on an article about the Eiffel Tower's expensive maintenance. The paper flexes realistically in his hands, "
"coffee steam curls beside it, shallow depth of field. Slow camera push toward the newspaper and his focused eyes."
),
7: STYLE+VICTOR+(
"Tight close-up on Victor reading the newspaper. His expression shifts almost imperceptibly from casual interest to focused calculation. "
"His eyes lift toward the rain-streaked cafe window where the Eiffel Tower is visible in the distance. "
"A restrained half-smile begins. Very slow dramatic push-in, nuanced facial animation, stable identity."
),
8: STYLE+VICTOR+(
"Over-the-shoulder close shot at the cafe table. Victor's finger traces the maintenance-cost story, then slowly circles the paragraph. "
"He looks from the newspaper to the Eiffel Tower outside and back again. His posture stills as the idea lands. "
"The camera glides from the article up to his face and ends on a subtle calculating smile. This is only the beginning of the story."
),
}

def copy_result(result, out):
    src=result[0] if isinstance(result,(tuple,list)) else result
    if isinstance(src,dict):
        src=src.get("path") or src.get("url")
    if not src:
        raise RuntimeError(f"No path returned: {result}")
    if str(src).startswith("http"):
        urllib.request.urlretrieve(src,out)
    else:
        shutil.copy2(src,out)

def retry(fn, label, attempts=4):
    err=None
    for n in range(1,attempts+1):
        try:
            print(f"{label}: attempt {n}",flush=True)
            return fn()
        except Exception as e:
            err=e
            print(f"{label} failed: {e}",flush=True)
            if n<attempts:
                time.sleep(35*n)
    raise err

def t2v_shot(idx):
    seed=192500+idx*101
    r=retry(lambda: t2v.predict(
        PROMPTS[idx], None, 1024, 576, 4.0, False, seed, False, "diffusion",
        api_name="/generate_video"), f"T2V shot {idx}")
    copy_result(r,f"raw_{idx}.mp4")

def msr_shot(idx, ref):
    seed=192500+idx*101
    r=retry(lambda: msr.predict(
        PROMPTS[idx], handle_file(ref), None, None, None, None,
        "1280 × 704 · 16:9", 4.0, 33, seed, False,
        api_name="/generate"), f"MSR shot {idx}")
    copy_result(r,f"raw_{idx}.mp4")

# First two shots establish setting + Victor.
t2v_shot(1)
t2v_shot(2)

# Extract a clean Victor reference from the introduction shot.
subprocess.run(["ffmpeg","-y","-loglevel","error","-ss","2.15","-i","raw_2.mp4","-frames:v","1","-q:v","2","victor_ref.jpg"],check=True)

# Use LTX-2.5 multi-subject reference to preserve Victor across the remaining scenes.
for idx in range(3,9):
    msr_shot(idx,"victor_ref.jpg")

# Normalize all shots to identical delivery specs while keeping their generated ambience.
for idx in range(1,9):
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i",f"raw_{idx}.mp4",
        "-vf","scale=1280:720:force_original_aspect_ratio=increase,crop=1280:720,fps=24",
        "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-ac","2",
        f"shot_{idx}.mp4"
    ],check=True)

with open("concat.txt","w",encoding="utf-8") as f:
    for idx in range(1,9):
        f.write(f"file '{os.path.abspath(f'shot_{idx}.mp4')}'\n")

subprocess.run([
    "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","concat.txt",
    "-t","30","-c:v","copy","-c:a","aac","-b:a","160k","visual_ambient.mp4"
],check=True)

# Free/open-source Kokoro narration.
def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"; voices="voices-v1.0.bin"
if not os.path.exists(model):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

narration=(
"In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
"His name was Victor Lustig, and he had a gift for making impossible lies sound completely reasonable. "
"One morning in Paris, he opened a newspaper and found a story complaining about the cost of maintaining the tower. "
"Most people would have read it and moved on. Lustig didn't."
)
k=Kokoro(model,voices)
v,sr=k.create(narration,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice_raw.wav",v,sr)
vd=len(v)/sr
if vd>29.35:
    fac=vd/29.35
    subprocess.run(["ffmpeg","-y","-loglevel","error","-i","voice_raw.wav","-filter:a",f"atempo={fac:.6f}","voice.wav"],check=True)
else:
    shutil.copy2("voice_raw.wav","voice.wav")

# Keep generated ambience low under narration; no paid music or voice services.
subprocess.run([
    "ffmpeg","-y","-loglevel","error",
    "-i","visual_ambient.mp4","-i","voice.wav",
    "-filter_complex",
    "[0:a]volume=0.20[amb];[1:a]highpass=f=70,lowpass=f=15500,volume=1.05[vo];[amb][vo]amix=inputs=2:duration=first:dropout_transition=0[a]",
    "-map","0:v:0","-map","[a]","-t","30",
    "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",
    "Rarely_Told_AI_First_30s_V5.mp4"
],check=True)

print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Rarely_Told_AI_First_30s_V5.mp4"
]).decode())
