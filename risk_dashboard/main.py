# main.py

from ui.app import app, theme

def main():
    demo = app()  # Gradio Blocks erzeugen
    demo.launch(share=True, server_name="0.0.0.0", server_port=7860, theme=theme)

if __name__ == "__main__":
    main()
