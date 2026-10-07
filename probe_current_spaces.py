from gradio_client import Client
spaces=[
    "Goalsave/ltx-2-5-studio",
]
for s in spaces:
    print("\\nSPACE",s)
    try:
        c=Client(s)
        print(c.view_api(return_format="dict"))
    except Exception as e:
        print("ERR",repr(e))
