# src/ui/__main__.py
"""Entry point for running the Gradio dashboard"""

from .app import create_ui

if __name__ == "__main__":
    ui = create_ui()
    ui.launch(inbrowser=True)
