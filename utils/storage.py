import json, os
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "..", "bot_config.json")

def _load():
    try: return json.load(open(CONFIG_FILE,"r",encoding="utf-8"))
    except: return {}

def _save(data): 
    json.dump(data, open(CONFIG_FILE,"w",encoding="utf-8"), ensure_ascii=False, indent=2)

def set_api_key(user_id:int, api_key:str):
    data=_load(); uid=str(user_id)
    data.setdefault(uid, {})["api_key"]=api_key
    _save(data)

def get_api_key(user_id:int): 
    return _load().get(str(user_id), {}).get("api_key")

def delete_api_key(user_id:int):
    data=_load(); uid=str(user_id)
    data.get(uid, {}).pop("api_key", None)
    _save(data)

