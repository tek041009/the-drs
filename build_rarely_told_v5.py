import os, shutil, subprocess, time, urllib.request, sys
from gradio_client import Client, handle_file
import soundfile as sf
from kokoro_onnx import Kokoro

SPACE="ChopperBlu/ltx-2-5-demo"
client=Client(SPACE)

STYLE=(
"Current-generation 2026 cinematic stylized 3D animated feature-film quality, polished realistic human proportions, "
"stable anatomy and hands, coherent recurring faces, detailed skin and cloth, rich physically plausible materials, "
"soft global illumination, atmospheric depth, cinematic depth of field, authentic 1920s Paris production design, "
"smooth deliberate camera motion, natural secondary motion and believable object contact. No on-screen text, no subtitles, "
"no watermark, no logos, no spoken dialogue, only natural period ambience and foley. "
)
VICTOR=(
"Victor Lustig is the same recurring character: a handsome European man in his late thirties, slim build, narrow oval face, "
"neat dark pencil moustache, dark brown hair beneath a charcoal fedora, tailored charcoal 1920s three-piece suit, cream shirt, "
"muted gold tie and polished black shoes. "
)

PROMPT_A=(
STYLE+
"Create one continuous fifteen-second multi-shot sequence with four clearly separated cinematic shots. "
"Shot one: wide golden-hour Paris in 1925, the Eiffel Tower dominating the skyline above a lively Haussmann boulevard; authentic period cars roll through traffic, pedestrians cross naturally, cafe awnings move subtly in the breeze, and the camera performs a slow crane-and-dolly forward. "
"A hard cut transitions to shot two. "+VICTOR+
"Victor walks confidently toward camera along the boulevard while the camera tracks backward at chest height; his coat and tie move naturally, feet contact the pavement correctly, pedestrians and cars pass coherently behind him, and the Eiffel Tower remains softly visible in the haze. "
"A hard cut transitions to shot three. "+VICTOR+
"Inside an opulent Paris hotel lounge, Victor calmly charms two wealthy businessmen with measured natural hand gestures; marble, brass and art-deco lamps glow around them as the camera makes a slow elegant arc. "
"A hard cut transitions to shot four. "+VICTOR+
"Morning in an elegant rain-lit Paris cafe; Victor sits alone beside a tall window with an espresso as a waiter enters and places a folded newspaper on his table. The camera gently dollies closer as Victor reaches for it. Maintain Victor's exact face, clothes and proportions across every cut."
)

PROMPT_B=(
STYLE+
"Continue directly from the supplied starting frame and preserve the exact same Victor Lustig identity, cafe, lighting, clothes and weather. "
+VICTOR+
"Create one continuous fifteen-second multi-shot sequence with three clearly separated cinematic shots. "
"Shot one: Victor naturally unfolds the newspaper with realistic paper flex and scans the page; espresso steam curls beside him, rain traces the window, and the camera pushes slowly from a medium view toward his hands and focused eyes. Do not show readable newspaper text. "
"A hard cut transitions to shot two. "+VICTOR+
"Tight close-up as his expression changes almost imperceptibly from casual interest to concentrated calculation; his eyes lift from the paper toward the rain-streaked window, then a restrained half-smile begins. Keep facial identity perfectly stable and nuanced. "
"A hard cut transitions to shot three. "+VICTOR+
"Over Victor's shoulder, the Eiffel Tower is framed through the rain-streaked window. Victor lowers the paper slightly, studies the tower, glances back down, then gives the tiniest calculating smile as the idea lands. The camera glides gently from the newspaper toward the tower and settles on Victor's profile. End on intrigue rather than resolution."
)

def is_quota_error(exc):
    s=str(exc).lower()
    return any(x in s for x in (
        "zerogpu", "quota", "runs limit", "maximum allowed", "subscribe to hugging face pro"
    ))

def save_result(result,out):
    src=result[0] if isinstance(result,(tuple,list)) else result
    if isinstance(src,dict):
        src=src.get("path") or src.get("url")
    if not src:
        raise RuntimeError(f"No path returned: {result}")
    if str(src).startswith("http"):
        urllib.request.urlretrieve(src,out)
    else:
        shutil.copy2(src,out)

def generate(prompt, image, duration, seed, out):
    last=None
    for attempt in range(1,3):
        try:
            print(f"Generating {out}, attempt {attempt}",flush=True)
            result=client.predict(
                prompt,
                handle_file(image) if image else None,
                1024,
                576,
                float(duration),
                False,
                int(seed),
                False,
                "diffusion",
                api_name="/generate_video",
            )
            save_result(result,out)
            return
        except Exception as e:
            last=e
            print(f"Generation failed: {e}",flush=True)
            if is_quota_error(e):
                with open("QUOTA_BLOCKED.txt","w",encoding="utf-8") as f:
                    f.write(str(e))
                sys.exit(75)
            if attempt < 2:
                time.sleep(35)
    raise last

# Call 1: 15 seconds, four native multishot scenes.
generate(PROMPT_A, None, 15.0, 1925, "segment_a.mp4")

# Carry the final visual state into generation B so the identity/environment bridge is automatic.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-sseof","-0.08","-i","segment_a.mp4",
    "-frames:v","1","-q:v","2","bridge_frame.jpg"
],check=True)

# Call 2: continue from the final frame for another 15 seconds / three scenes.
generate(PROMPT_B, "bridge_frame.jpg", 15.0, 1925, "segment_b.mp4")

# Normalize the two current-generation segments.
for src,out in [("segment_a.mp4","a_norm.mp4"),("segment_b.mp4","b_norm.mp4")]:
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i",src,
        "-vf","scale=1280:720:flags=lanczos,fps=24",
        "-c:v","libx264","-preset","fast","-crf","18","-pix_fmt","yuv420p",
        "-c:a","aac","-b:a","160k","-ar","48000","-ac","2",out
    ],check=True)

with open("concat.txt","w",encoding="utf-8") as f:
    f.write(f"file '{os.path.abspath('a_norm.mp4')}'\n")
    f.write(f"file '{os.path.abspath('b_norm.mp4')}'\n")
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-f","concat","-safe","0","-i","concat.txt",
    "-t","30","-c:v","copy","-c:a","aac","-b:a","160k","visual_ambient.mp4"
],check=True)

# Accepted free Kokoro narrator.
def dl(url,fn):
    req=urllib.request.Request(url,headers={"User-Agent":"RarelyTold/1.0"})
    with urllib.request.urlopen(req,timeout=120) as r, open(fn,"wb") as w:
        while True:
            c=r.read(1024*1024)
            if not c: break
            w.write(c)

model="kokoro-v1.0.int8.onnx"
voices="voices-v1.0.bin"
if not os.path.exists(model):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/kokoro-v1.0.int8.onnx",model)
if not os.path.exists(voices):
    dl("https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.1/voices-v1.0.bin",voices)

script=(
"In 1925, one man managed to sell the Eiffel Tower. Not a souvenir. The actual tower. "
"His name was Victor Lustig, and he had a gift for making impossible lies sound completely reasonable. "
"One morning in Paris, he opened a newspaper and found a story complaining about the cost of maintaining the tower. "
"Most people would have read it and moved on. Lustig didn't."
)
k=Kokoro(model,voices)
v,sr=k.create(script,voice="bm_george",speed=1.03,lang="en-gb")
sf.write("voice_raw.wav",v,sr)
dur=len(v)/sr
if dur>29.35:
    fac=dur/29.35
    subprocess.run([
        "ffmpeg","-y","-loglevel","error","-i","voice_raw.wav",
        "-filter:a",f"atempo={fac:.6f}","voice.wav"
    ],check=True)
else:
    shutil.copy2("voice_raw.wav","voice.wav")

# Preserve generated foley/ambience quietly under narration.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","visual_ambient.mp4","-i","voice.wav",
    "-filter_complex",
    "[0:a]volume=0.13[amb];[1:a]highpass=f=70,lowpass=f=15500,volume=1.05[vo];[amb][vo]amix=inputs=2:duration=first:dropout_transition=0[a]",
    "-map","0:v:0","-map","[a]","-t","30",
    "-c:v","copy","-c:a","aac","-b:a","192k","-movflags","+faststart",
    "Rarely_Told_AI_First_30s_V7.mp4"
],check=True)

# Contact sheet for automatic/visual QA.
subprocess.run([
    "ffmpeg","-y","-loglevel","error","-i","Rarely_Told_AI_First_30s_V7.mp4",
    "-vf","fps=1/2.5,scale=320:-2,tile=4x3","-frames:v","1","Rarely_Told_V7_Contact.jpg"
],check=True)

print(subprocess.check_output([
    "ffprobe","-v","error","-show_entries","format=duration,size","-of","default=nw=1",
    "Rarely_Told_AI_First_30s_V7.mp4"
]).decode())
