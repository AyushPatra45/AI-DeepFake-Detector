"""Start the local app from any working directory without reusing an occupied port."""
from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

import uvicorn


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    root = Path(__file__).resolve().parents[1]
    os.chdir(root)
    sys.path.insert(0, str(root / "backend"))
    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    for port in range(args.port, min(args.port + 20, 65536)):
        try:
            listener.bind(("127.0.0.1", port))
            break
        except OSError:
            continue
    else:
        listener.close()
        parser.error("No local port available in the requested range")
    try:
        print(f"Forensic workspace: http://127.0.0.1:{port}", flush=True)
        uvicorn.Server(uvicorn.Config("app.main:app", host="127.0.0.1", port=port)).run(
            sockets=[listener]
        )
    finally:
        listener.close()


if __name__ == "__main__":
    main()
