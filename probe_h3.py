from gradio_client import Client
c=Client("amisima/Minimax-H3-Studio-Turbo")
print(c.view_api(return_format="dict"))
