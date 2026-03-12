import json
import time

def log_trade(trade):

    trade["timestamp"] = int(time.time())

    with open("atlas_trades.json","a") as f:
        f.write(json.dumps(trade)+"\n")