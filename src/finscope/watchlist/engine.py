import json
from pathlib import Path

_DEFAULT_FILE = Path.home() / ".finscope" / "watchlist.json"

class Watchlist:
    def __init__(self, path=None):
        self._path = Path(path) if path else _DEFAULT_FILE
        self._symbols = []
        self._load()

    def _load(self):
        if self._path.exists():
            try: self._symbols = json.loads(self._path.read_text()).get("symbols", [])
            except: self._symbols = []

    def _save(self):
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps({"symbols": self._symbols}, indent=2))

    def add(self, *symbols):
        for s in symbols:
            if s.upper() not in self._symbols: self._symbols.append(s.upper())
        self._save()

    def remove(self, *symbols):
        for s in symbols:
            if s.upper() in self._symbols: self._symbols.remove(s.upper())
        self._save()

    def clear(self): self._symbols = []; self._save()
    @property
    def is_empty(self): return not self._symbols
    @property
    def symbols(self): return self._symbols

    def snapshot(self):
        import finscope
        if self.is_empty: return []
        return [vars(d) for d in finscope.compare(*self._symbols)]
