import sys
import time
import websocket

url = "ws://127.0.0.1:10102/log/"
out = open(sys.argv[1] if len(sys.argv) > 1 else "ws_log.txt", "w", encoding="utf-8", buffering=1)
out.write("connecting " + url + "\n")


def on_message(ws, message):
    out.write(message + "\n")


def on_error(ws, error):
    out.write("ERROR " + repr(error) + "\n")


def on_open(ws):
    out.write("OPEN\n")


def on_close(ws, code, reason):
    out.write(f"CLOSE {code} {reason}\n")


ws = websocket.WebSocketApp(url, on_open=on_open, on_message=on_message, on_error=on_error, on_close=on_close)
ws.run_forever(ping_interval=10, ping_timeout=5)
