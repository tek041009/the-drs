import json, sys, os

p=sys.argv[1] if len(sys.argv)>1 else "workflow.json"
with open(p,"r",encoding="utf-8") as f:
    w=json.load(f)

shot=int(os.environ.get("SHOT","1"))
nodes={n["id"]:n for n in w["nodes"]}

CHAR=("same recurring character, Victor Lustig: handsome European man in his late thirties, slim build, "
      "narrow oval face, neat dark pencil moustache, dark brown hair under a charcoal fedora, "
      "tailored charcoal 1920s three-piece suit, cream shirt, muted gold tie, polished black shoes. ")
STYLE=("high-end cinematic stylized 3D animated feature film, realistic human proportions, refined expressive facial rig, "
       "detailed cloth and skin materials, premium theatrical animation, sophisticated art direction, warm 1920s Paris palette, "
       "soft global illumination, atmospheric depth, cinematic depth of field, fluid believable motion, subtle secondary motion, no text. ")

prompts={
1: STYLE+"Wide establishing shot of Paris in 1925 at golden hour. The Eiffel Tower dominates the skyline beyond a lively boulevard. Period cars roll through traffic, pedestrians move naturally, cafe awnings ripple in the breeze, smoke and haze catch the sun. Slow cinematic crane forward toward the tower, grand and intriguing.",
2: STYLE+CHAR+"He walks confidently toward camera down a busy Paris boulevard. Period cars pass behind him and pedestrians weave around him. The camera tracks backward smoothly at chest height; his coat and tie move naturally. The Eiffel Tower sits softly in the distant haze.",
3: STYLE+CHAR+"Medium close tracking shot from three-quarter profile as Victor moves through an upscale Paris crowd. He smiles faintly, studies people around him, and adjusts one cuff with practiced confidence. Elegant hotel facades and warm shop windows slide by in deep parallax. Smooth lateral dolly.",
4: STYLE+CHAR+"Inside an opulent 1920s Paris hotel lobby, Victor calmly charms two wealthy businessmen in suits. He gestures with relaxed confidence while they listen closely, then gives a tiny knowing smile. Marble, brass, art deco lamps, polished floors, background guests moving naturally. Slow circular camera move.",
5: STYLE+CHAR+"Morning in an elegant Paris cafe. Victor sits alone by a large window with a small espresso. A folded newspaper is placed onto the table by a waiter entering frame. Victor reaches for it. Outside, pedestrians and period cars move through soft morning rain. Intimate cinematic dolly in.",
6: STYLE+CHAR+"Close cinematic shot at the cafe table. Victor unfolds a large 1920s French newspaper and scans the page. His finger stops on a story about the Eiffel Tower's expensive maintenance. Paper flexes realistically in his hands, coffee steam curls nearby, shallow depth of field. Camera slowly pushes toward the article and his eyes.",
7: STYLE+CHAR+"Tight close-up on Victor reading the newspaper. His expression changes almost imperceptibly from casual interest to focused calculation; his eyes lift toward the window where the Eiffel Tower can be seen in the distance. A subtle half-smile forms. Very slow dramatic push-in, nuanced facial animation.",
8: STYLE+CHAR+"Cinematic imagination transition from Victor at the cafe to an elegant visual metaphor: the Eiffel Tower reflected in his eye dissolves into official-looking cream government papers, embossed seals and architectural lines spread across the table. His hand slides one document forward as the camera glides over the papers. Intriguing, clever, grounded, not magical fantasy."
}

neg=("low quality, cheap game graphics, low poly, blocky, flat shading, plastic toy, slideshow, powerpoint, "
     "static image, jitter, flicker, warped face, deformed hands, extra fingers, extra limbs, bad anatomy, duplicate people, "
     "rubbery motion, mushy details, blurry, noisy, oversharpened, text, subtitles, watermark")

nodes[6]["widgets_values"]=[prompts[shot]]
nodes[7]["widgets_values"]=[neg]
nodes[87]["widgets_values"]=["t5-v1_1-xxl-encoder-Q3_K_S.gguf","ltxv"]
nodes[78]["widgets_values"]=["ltxv-2b-0.9.6-distilled-04-25-Q4_K_S.gguf"]
# Slight quality bump over the proof shot while keeping CPU generation practical.
nodes[70]["widgets_values"]=[576,320,97,1]
nodes[71]["widgets_values"]=[8,2.05,0.95,True,0.1]
nodes[86]["widgets_values"]=[f"rarely_told_v4_shot_{shot}","vp9",25.0,24]

# Hold a consistent seed family across shots to stabilize style/identity.
for n in w["nodes"]:
    if n.get("type")=="RandomNoise" and n.get("widgets_values"):
        n["widgets_values"][0]=624190 + shot*17

for link in w["links"]:
    if link[0] in (188,189):
        link[1]=87
        link[2]=0
nodes[87]["outputs"][0]["links"]=[188,189]
nodes[81]["outputs"][0]["links"]=[]
w["nodes"]=[n for n in w["nodes"] if n["id"] != 81]
w["links"]=[ln for ln in w["links"] if ln[1] != 81 and ln[3] != 81]

with open(p,"w",encoding="utf-8") as f:
    json.dump(w,f,separators=(",",":"))
print("patched",p,"shot",shot)
