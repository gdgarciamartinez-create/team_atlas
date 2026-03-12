import requests

TOKEN = "TU_TOKEN"
CHAT_ID = "TU_CHAT"


def send_signal(trade):

    text = f"""
ATLAS SIGNAL

{trade['symbol']} {trade['tf']}

Entry: {trade['entry']}
SL: {trade['sl']}
TP: {trade['tp']}

Lot: {trade['lot']}
Score: {trade['score']}
"""

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"

    requests.post(url, json={
        "chat_id":CHAT_ID,
        "text":text
    })