"""Profile-owned, game-specific memories of facts a rival actually witnessed."""
import math

GAMES = ('texas_holdem', 'five_card_draw', 'seven_card_stud')
ACTIONS = {'check', 'bet', 'call', 'raise', 'fold'}


def new_learning():
    return {'version': 1, 'games': {}}


def normalize_learning(value):
    result = new_learning()
    if not isinstance(value, dict) or not isinstance(value.get('games'), dict):
        return result
    for game in GAMES:
        source = value['games'].get(game)
        if not isinstance(source, dict):
            continue
        observers = {}
        for identity, targets in list(source.items())[-256:]:
            if not isinstance(identity, str) or not isinstance(targets, dict):
                continue
            cleaned = {}
            for target, record in list(targets.items())[-256:]:
                if not isinstance(target, str) or not isinstance(record, dict):
                    continue
                history = []
                raw = record.get('history', [])
                for item in raw[-96:] if isinstance(raw, list) else []:
                    if not isinstance(item, (list, tuple)) or len(item) != 4:
                        continue
                    action, street, pressure, size = item
                    if not isinstance(action, str) or action not in ACTIONS or not isinstance(street, str):
                        continue
                    if not isinstance(size, (float, int)) or not math.isfinite(size):
                        continue
                    history.append([action, street[:24], bool(pressure), max(0, min(100000, size))])
                raw = record.get('reveals', [])
                reveals = [v for v in raw[-24:] if isinstance(v, bool)] if isinstance(raw, list) else []
                cleaned[target] = {'history': history, 'reveals': reveals}
            observers[identity[:160]] = cleaned
        result['games'][game] = observers
    return result


class RivalLearning:
    def __init__(self, store, game, identities):
        self.identities = identities
        self.banks = {}
        self.active_observers = set(identities.values())
        if not isinstance(store, dict):
            return
        observers = store.setdefault('games', {}).setdefault(game, {})
        for seat, identity in identities.items():
            if seat:
                self.banks[identity] = observers.setdefault(identity, {})

    def record(self, seat, field, item):
        target = self.identities.get(seat)
        if target is None:
            return
        for observer, bank in self.banks.items():
            if observer == target or observer not in self.active_observers:
                continue
            record = bank.setdefault(target, {'history': [], 'reveals': []})
            samples = record[field]
            samples.append(list(item) if field == 'history' else bool(item))
            del samples[:max(0, len(samples) - (96 if field == 'history' else 24))]

    def samples(self, observer, seat):
        bank = self.banks.get(observer)
        if bank is None:
            return None
        return bank.get(self.identities.get(seat), {'history': [], 'reveals': []})
