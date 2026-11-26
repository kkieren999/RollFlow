"""Internal launcher for the loopback WSGI server."""
from pathlib import Path
import sys
from deployment.native import load, serve

if __name__ == "__main__":
    serve(load(Path(sys.argv[1])))
