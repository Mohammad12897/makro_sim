#*** a/run.py
#--- b/run.py
#@@ -1,41 +1,41 @@
#!/usr/bin/env python3
import argparse
import sys
from pathlib import Path
 
# Importiere das bereits aufgebaute Gradio-Interface (demo) und die Lexikon-Funktion
from src.ui.gradio_app import demo, lexikon_erweitert_markdown
 
def parse_args(argv=None):
     parser = argparse.ArgumentParser(description="Start Gradio demo oder gib das Lexikon aus.")
     parser.add_argument("--lexikon", action="store_true", help="Gibt das Lexikon-Markdown auf stdout aus")
     parser.add_argument("--lexikon-out", type=str, default=None, help="Schreibt das Lexikon-Markdown in die angegebene Datei")
     #parser.add_argument("--share", action="store_true", help="Gradio share=True setzen (öffentliche URL)")
     parser.add_argument("--no-share", action="store_true", help="Disable Gradio share (default: enabled)")
     parser.add_argument("--server-name", type=str, default=None, help="Optional: server_name für demo.launch")
     parser.add_argument("--server-port", type=int, default=None, help="Optional: server_port für demo.launch")
     return parser.parse_args(argv)
 
def main(argv=None):
     args = parse_args(argv)
 
     if args.lexikon:
         md = lexikon_erweitert_markdown()
         if args.lexikon_out:
             out_path = Path(args.lexikon_out)
             out_path.write_text(md, encoding="utf-8")
             print(f"Lexikon geschrieben nach: {out_path}", file=sys.stderr)
             return 0
         else:
             print(md)
             return 0
 
     # Standard: Gradio-App starten
     launch_kwargs = {}
     #if args.share:
         #launch_kwargs["share"] = True
     # Default: share aktivieren, kann mit --no-share deaktiviert werden
     launch_kwargs["share"] = True
     if args.no_share:
         launch_kwargs["share"] = False
     if args.server_name:
         launch_kwargs["server_name"] = args.server_name
     if args.server_port:
         launch_kwargs["server_port"] = args.server_port
 
     try:
         # demo ist das gr.Blocks()-Objekt aus src.ui.gradio_app
         demo.launch(**launch_kwargs)
     except Exception as e:
         print(f"Fehler beim Starten der Gradio-App: {e}", file=sys.stderr)
         return 1
 
     return 0
 
if __name__ == "__main__":
     sys.exit(main())
