from gradio_client import Client
import os, shutil

client=Client("ChopperBlu/ltx-2-5-demo")
prompt=(
"High-end 2026 cinematic stylized 3D animated feature-film shot set inside an elegant Paris cafe in 1925. "
"Victor Lustig is the exact same recurring character: a handsome European man in his late thirties with a slim build, narrow oval face, neat dark pencil moustache, dark brown hair beneath a charcoal fedora, tailored charcoal 1920s three-piece suit, cream shirt, muted gold tie and polished black shoes. "
"He sits alone at a small table beside a rain-streaked window. A waiter places a folded French newspaper on the table; Victor reaches for it and begins to unfold it with realistic paper motion. Espresso steam curls beside him. "
"The camera performs a slow intimate dolly-in from medium shot toward Victor. His face remains stable and detailed, hands stay anatomically coherent, contact with the newspaper is physically believable, background patrons move naturally. "
"Premium theatrical 3D animation, rich materials, realistic proportions, nuanced expression, soft global illumination, atmospheric depth, cinematic depth of field, crisp coherent geometry, physically believable motion, no text, no watermark."
)
result=client.predict(
    prompt,
    None,
    1024,
    576,
    4.0,
    False,
    1925,
    False,
    "diffusion",
    api_name="/generate_video",
)
print("RESULT",result)
video=result[0]
if isinstance(video, dict):
    path=video.get("path") or video.get("url")
else:
    path=video
if not path:
    raise RuntimeError("no video path returned")
if str(path).startswith("http"):
    import urllib.request
    urllib.request.urlretrieve(path,"Rarely_Told_V5_Shot1.mp4")
else:
    shutil.copy2(path,"Rarely_Told_V5_Shot1.mp4")
print("saved",os.path.getsize("Rarely_Told_V5_Shot1.mp4"))
