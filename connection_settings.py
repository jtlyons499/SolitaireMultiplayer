"""Small user-local connection preferences, separate from career profiles."""
import json
import os
from pathlib import Path

def path():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'.config'))/'SolitaireMultiplayer'/'connection.json'
def load():
    try:
        data=json.loads(path().read_text(encoding='utf-8'))
        return {k:str(data.get(k,''))[:128] for k in ('name','relay_address')}
    except (OSError,ValueError,AttributeError):return {}
def save(name,address):
    try:
        target=path();target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text(json.dumps({'name':name,'relay_address':address}),encoding='utf-8')
    except OSError:pass
