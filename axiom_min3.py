#!/usr/bin/env python3
"""AXIOM min3. gamma = time + project + topic. delta = updates. mold is axiom_min.py.

No new layer:
  - IS is Δ only. facts stay inside αβ
  - latest/is_lines default exact=True
  - write_delta calls gate(). NONE drops. HUMAN queues
  - render prints the full γ address from the filter
"""
from __future__ import annotations
import hashlib, json, time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Optional

IS_MAX = 3
ETA_HIGH = 0.35
WORDS = frozenset({"課題", "改善点", "結論", "立場", "状態"})
WORD_ALIAS = {"issue": "課題", "improve": "改善点", "improvement": "改善点", "conclusion": "結論", "position": "立場", "status": "状態", "state": "状態"}

def _sha(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()

def canon_word(field: str) -> str:
    f = field.strip()
    return WORD_ALIAS.get(f, WORD_ALIAS.get(f.lower(), f))

def coarse_time(label: str, grain: str = "month") -> str:
    s = label.strip().replace("/", "-")
    if grain == "week" and len(s) >= 10:
        return s[:10]
    return s[:7] if len(s) >= 7 else s

def gamma_line(filt: dict) -> str:
    parts = [filt.get(k, "") for k in ("time_label", "project", "topic")]
    return " / ".join(p for p in parts if p) or "(unscoped)"

@dataclass(frozen=True)
class Alpha:
    rules: tuple[str, ...] = ("βを遵守する", "核を動かさない", "今のγ住所の外を補完しない", "βとΔを混ぜない")

@dataclass(frozen=True)
class Beta:
    name: str
    tone: str
    center: str
    values: tuple[str, ...]

@dataclass(frozen=True)
class BetaFact:
    knowledge_id: str
    field: str
    value: str

@dataclass
class Inner:
    alpha: Alpha
    beta: Beta
    facts: tuple[BetaFact, ...] = ()
    hash_a: str = ""
    def payload(self):
        return {"alpha": list(self.alpha.rules), "beta": {"name": self.beta.name, "tone": self.beta.tone, "center": self.beta.center, "values": list(self.beta.values)}, "facts": [asdict(f) for f in self.facts]}
    def compute_hash(self):
        return _sha(self.payload())
    def seal(self):
        self.hash_a = self.compute_hash(); return self
    def intact(self):
        return bool(self.hash_a) and self.hash_a == self.compute_hash()
    def fact_lines(self):
        return [f"{f.field}={f.value}" for f in self.facts]

@dataclass(frozen=True)
class Gamma:
    time_label: str = ""
    project: str = ""
    topic: str = ""
    def matches(self, filt, exact=True):
        for k, v in filt.items():
            if not hasattr(self, k): return False
            val = getattr(self, k)
            if exact and val != v: return False
            if not exact and v.lower() not in val.lower(): return False
        return True
    def label(self):
        return " / ".join(p for p in (self.time_label, self.project, self.topic) if p) or "(unscoped)"
    def key(self):
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

GammaIndex = Gamma

@dataclass(frozen=True)
class Delta:
    field: str
    old_value: Optional[str]
    new_value: str
    timestamp: float
    source_id: str = ""
    reason: str = ""
    def line(self):
        return f"{self.field}={self.new_value}" if self.old_value is None else f"{self.field}:{self.old_value}->{self.new_value}"

DeltaIndex = Delta

@dataclass
class Eta:
    pull: float = 0.0
    streak: int = 0
    def step(self, tone, identity, values):
        gap = 0.45*(1-tone)+0.40*(1-identity)+0.15*(1-values)
        self.pull = max(0.0, min(1.0, gap))
        if self.pull >= 0.30: self.streak += 1
        else:
            self.streak = 0; self.pull *= 0.45
    def high(self):
        return self.pull >= ETA_HIGH

class Write:
    NONE = "none"; DELTA = "delta"; HUMAN = "needs_human"; UNKNOWN_WORD = "unknown_word"

def gate(eta, identity, human):
    if identity < 0.20: return Write.NONE
    if human: return Write.HUMAN
    return Write.DELTA

class Capsule:
    def __init__(self, inner: Inner):
        self.inner = inner.seal()
        self._deltas = []
        self._pending = []
        self._index = defaultdict(list)
        self._adopted = set()
        self.eta = Eta()
        self.last_write = Write.NONE
    def allowed_words(self):
        return frozenset(WORDS | self._adopted)
    def adopt_word(self, field):
        w = canon_word(field); self._adopted.add(w); return w
    def _index_put(self, g):
        k = f"{g.project}::{g.topic}"
        if g not in self._index[k]: self._index[k].append(g)
    def _prepare_address(self, address, grain="month"):
        if address.time_label:
            return Gamma(**{**asdict(address), "time_label": coarse_time(address.time_label, grain=grain)})
        return address
    def write_delta(self, address, field, new_value, old_value=None, source_id="", reason="", keep_history=True, human=False, identity=1.0, grain="month"):
        word = canon_word(field)
        if word not in self.allowed_words():
            self.last_write = Write.UNKNOWN_WORD
            return None
        decision = gate(self.eta, identity, human)
        self.last_write = decision
        if decision == Write.NONE:
            return None
        address = self._prepare_address(address, grain=grain)
        d = Delta(word, old_value, new_value, time.time(), source_id, reason)
        if decision == Write.HUMAN:
            self._pending.append((address, d))
            return None
        return self._commit(address, d, keep_history=keep_history)
    def _commit(self, address, d, keep_history=True):
        if not keep_history:
            self._deltas = [(c, x) for c, x in self._deltas if not (c == address and x.field == d.field)]
        self._deltas.append((address, d))
        self._index_put(address)
        self.last_write = Write.DELTA
        return d
    def pending(self):
        return list(self._pending)
    def approve_pending(self, index=-1, keep_history=True):
        if not self._pending:
            return None
        address, d = self._pending.pop(index)
        return self._commit(address, d, keep_history=keep_history)
    def reject_pending(self, index=-1):
        if not self._pending:
            return None
        return self._pending.pop(index)
    def query_delta(self, filt, exact=True):
        return [(g, d) for g, d in self._deltas if g.matches(filt, exact=exact)]
    def query_gamma(self, filt, exact=True):
        if "project" in filt and "topic" in filt and exact:
            cand = self._index.get(f"{filt['project']}::{filt['topic']}", [])
        else:
            cand = [c for c, _ in self._deltas]
        out = []
        for g in cand:
            if g.matches(filt, exact=exact) and g not in out:
                out.append(g)
        return out
    def latest_at(self, filt, exact=True):
        last = {}
        for _, d in self.query_delta(filt, exact=exact):
            last[d.field] = d
        return list(last.values())
    def latest(self, filt, word, exact=True):
        word = canon_word(word)
        found = [d for _, d in self.query_delta(filt, exact=exact) if d.field == word]
        return found[-1] if found else None
    def history(self, filt, word, exact=True):
        word = canon_word(word)
        return [d for _, d in self.query_delta(filt, exact=exact) if d.field == word]
    def lookup(self, word):
        word = canon_word(word)
        out = []
        for g, d in self._deltas:
            if d.field == word and g not in out:
                out.append(g)
        return out
    def is_lines(self, filt, exact=True):
        lines = []
        for d in self.latest_at(filt, exact=exact):
            line = d.line()
            if line not in lines:
                lines.append(line)
        return lines[-IS_MAX:]
    def render(self, user, filt, exact=True):
        inn = self.inner
        if not inn.intact():
            bind = "核の整合性が壊れている。生成するな。"
        elif self.eta.high():
            bind = "偏差が大きい。基準へ戻せ。今の住所の外を埋めつな。核は書き換えるな。"
        else:
            bind = "基準に従って短く。更新と核を混ぜるな。核は変えるな。"
        facts = inn.fact_lines()
        fact_block = "\n".join(f"- {x}" for x in facts) if facts else "(none)"
        is_block = "\n".join(f"- {x}" for x in self.is_lines(filt, exact=exact)) or "(none)"
        return "\n".join([
            f"[αβ] {inn.hash_a[:16]} intact={inn.intact()}",
            f"name: {inn.beta.name}",
            f"tone: {inn.beta.tone}",
            f"center: {inn.beta.center}",
            f"values: {', '.join(inn.beta.values)}",
            "",
            "[β facts]",
            fact_block,
            "",
            "[γ address]",
            gamma_line(filt),
            "",
            "[IS]",
            is_block,
            "",
            "[bind]",
            bind,
            "",
            "[user]",
            user,
        ])
