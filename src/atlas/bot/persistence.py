import json, os, uuid, time

DATA = "data"
PARAMS = f"{DATA}/params_by_symbol_tf.json"
SCEN = f"{DATA}/scenarios.json"

os.makedirs(DATA, exist_ok=True)

def load_params(symbol, tf):
    if not os.path.exists(PARAMS): return {}
    with open(PARAMS) as f:
        return json.load(f).get(f"{symbol}|{tf}", {})

def save_params(symbol, tf, params):
    data = {}
    if os.path.exists(PARAMS):
        with open(PARAMS) as f: data = json.load(f)
    data[f"{symbol}|{tf}"] = params
    with open(PARAMS,"w") as f: json.dump(data,f,indent=2)

def load_scenarios():
    if not os.path.exists(SCEN): return []
    with open(SCEN) as f: return json.load(f)

def add_scenario(s):
    data = load_scenarios()
    s["id"] = str(uuid.uuid4())
    s["created_at"] = int(time.time())
    data.append(s)
    with open(SCEN,"w") as f: json.dump(data,f,indent=2)
    return s

def delete_scenario(id):
    data = [s for s in load_scenarios() if s["id"] != id]
    with open(SCEN,"w") as f: json.dump(data,f,indent=2)
    return {"ok": True}
