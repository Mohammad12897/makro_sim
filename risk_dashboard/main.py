# main.py


#from ui.app import build_app
from ui.app import create_gradio_app
from test.example_presets import EXAMPLE_PRESETS

if __name__ == "__main__":
    #app = build_app()
    app = create_gradio_app(EXAMPLE_PRESETS)
    app.launch(share=True)
