#!/usr/bin/env python3
"""AXIOM min3. gamma = time + project + topic. delta = updates. mold is axiom_min.py.

No new layer:
  - IS is Δ only. facts stay inside αβ
  - latest/is_lines default exact=True
  - exact=True equals supplied filter keys only; missing γ axes are wildcards
  - write_delta calls gate(). NONE drops. HUMAN queues
  - render prints supplied γ axes from the filter
  - latest is append order. η does not decide writes
  - LLM writes only via closed packet {gamma, delta, is}
  - IS is isolated from Δ. write_delta never adopts IS
  - query_gamma reads _index (IS-only addresses stay visible)
  - query/render coarsen time_label with the same grain as write
  - identity default 1.0. caller must pass it to trip the 0.20 gate
  - Delta.timestamp is audit only. latest stays append order
  - γ packet needs at least one axis. empty address is not an address
  - index grows only after a committed Δ or adopted IS
  - IS_MAX caps each address. render does not recut across addresses
"""
from __future__ import annotations
import hashlib, json, time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Any, Optional

IS_MAX = 3
ETA_HIGH = 0.35
WORDS = frozenset({"課題", "改善点", "結論", "立場", "状態"})
WORD_ALIAS = {"issue": "課題", "improve": "改善点", "improvement": "改善点", "conclusion": "結論", "position": "立場", "status": "状態", "state": "状態"}
PACKET_KEYS = frozenset({"gamma", "delta", "is"})
GAMMA_KEYS = frozenset({"time_label", "project", "topic"})
DELTA_KEYS = frozenset({"field", "new_value", "old_value", "source_id", "reason"})
IS_KEYS = frozenset({"field", "value"})
SNAP_DELTA_KEYS = frozenset({"field", "old_value", "new_value", "timestamp", "source_id", "reason"})

def _sha(obj):
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode()).hexdigest()

def canon_word(field: str) -> str:
    f = field.strip()
    return WORD_ALIAS.get(f, WORD_ALIAS.get(f.lower(), f))

def coarse_time(label: str, grain: str = "month") -> str:
    # footnote: grain="week" is YYYY-MM-DD prefix, not ISO week number.
    s = label.strip().replace("/", "-")
    if grain == "week" and len(s) >= 10:
        return s[:10]
    return s[:7] if len(s) >= 7 else s

def normalize_filt(filt, grain="month"):
    # write and query share this. day stored as month still matches "2026-08-15".
    out = dict(filt or {})
    if out.get("time_label"):
        out["time_label"] = coarse_time(str(out["time_label"]), grain=grain)
    return out

def gamma_line(filt: dict) -> str:
    # shows supplied dimensions only. missing axes stay blank, not inferred.
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
        # exact = equality on supplied keys only. unspecified γ axes stay wildcards.
        # exact does not mean "all three axes must be present".
        for k, v in filt.items():
            if not hasattr(self, k): return False
            val = str(getattr(self, k))
            needle = str(v)
            if exact and val != needle: return False
            if not exact and needle.lower() not in val.lower(): return False
        return True
    def label(self):
        return " / ".join(p for p in (self.time_label, self.project, self.topic) if p) or "(unscoped)"
    def key(self):
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)

GammaIndex = Gamma  # alias. index row is the address itself.

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

DeltaIndex = Delta  # alias. index row is the update itself.

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
    NONE = "none"; DELTA = "delta"; HUMAN = "needs_human"; UNKNOWN_WORD = "unknown_word"; BAD_PACKET = "bad_packet"; IS = "is"

def gate(eta: Eta, identity: float, human: bool) -> str:
    # eta kept for gate-policy compatibility. min3 write does not read it.
    _ = eta
    if identity < 0.20: return Write.NONE
    if human: return Write.HUMAN
    return Write.DELTA

def _closed(obj, allowed):
    if not isinstance(obj, dict):
        return None
    if set(obj) - allowed:
        return None
    return obj

def _strip_fence(raw: str) -> str:
    s = raw.strip()
    if not s.startswith("```"):
        return s
    s = s[3:]
    if s[:4].lower() == "json":
        s = s[4:]
    end = s.rfind("```")
    if end >= 0:
        s = s[:end]
    return s.strip()

def parse_packet(raw):
    """LLM -> index spec. JSON object or dict. No free-text parse."""
    if isinstance(raw, str):
        raw = _strip_fence(raw)
        try:
            raw = json.loads(raw)
        except json.JSONDecodeError:
            return None
    pkt = _closed(raw, PACKET_KEYS)
    if pkt is None:
        return None
    if "gamma" in pkt:
        g = _closed(pkt["gamma"], GAMMA_KEYS)
        if g is None:
            return None
        pkt = {**pkt, "gamma": g}
    if "delta" in pkt:
        if not isinstance(pkt["delta"], list):
            return None
        rows = []
        for row in pkt["delta"]:
            d = _closed(row, DELTA_KEYS)
            if d is None or "field" not in d or "new_value" not in d:
                return None
            rows.append(d)
        pkt = {**pkt, "delta": rows}
    if "is" in pkt:
        if not isinstance(pkt["is"], list):
            return None
        rows = []
        for row in pkt["is"]:
            item = _closed(row, IS_KEYS)
            if item is None or "field" not in item or "value" not in item:
                return None
            rows.append(item)
        pkt = {**pkt, "is": rows}
    if "gamma" not in pkt:
        return None
    g = pkt["gamma"]
    # footnote: an address needs a where. empty γ is not indexed.
    if not any(str(g.get(k, "")).strip() for k in ("time_label", "project", "topic")):
        return None
    return pkt

def _load_gamma(obj) -> Optional[Gamma]:
    g = _closed(obj, GAMMA_KEYS)
    if g is None:
        return None
    return Gamma(
        time_label=str(g.get("time_label", "")),
        project=str(g.get("project", "")),
        topic=str(g.get("topic", "")),
    )

def _load_delta(obj) -> Optional[Delta]:
    d = _closed(obj, SNAP_DELTA_KEYS)
    if d is None or "field" not in d or "new_value" not in d:
        return None
    try:
        ts = float(d.get("timestamp") or 0.0)
    except (TypeError, ValueError):
        return None
    return Delta(
        field=canon_word(str(d["field"])),
        old_value=None if d.get("old_value") is None else str(d["old_value"]),
        new_value=str(d["new_value"]),
        timestamp=ts,
        source_id=str(d.get("source_id", "")),
        reason=str(d.get("reason", "")),
    )

def packet_gamma(pkt) -> Gamma:
    g = pkt.get("gamma") or {}
    return Gamma(
        time_label=str(g.get("time_label", "")),
        project=str(g.get("project", "")),
        topic=str(g.get("topic", "")),
    )

class Capsule:
    def __init__(self, inner: Inner):
        self.inner = inner.seal()
        self._deltas = []
        self._pending = []
        self._is = {}
        self._is_pending = []
        self._index = defaultdict(list)
        self._by_project = defaultdict(list)
        self._by_topic = defaultdict(list)
        self._adopted = set()
        self.eta = Eta()
        self.last_write = Write.NONE
    def allowed_words(self):
        return frozenset(WORDS | self._adopted)
    def adopt_word(self, field):
        w = canon_word(field); self._adopted.add(w); return w
    def _index_put(self, g: Gamma) -> None:
        # buckets only. time is judged later by Gamma.matches.
        k = f"{g.project}::{g.topic}"
        if g not in self._index[k]:
            self._index[k].append(g)
        if g.project and g not in self._by_project[g.project]:
            self._by_project[g.project].append(g)
        if g.topic and g not in self._by_topic[g.topic]:
            self._by_topic[g.topic].append(g)
    def _prepare_address(self, address: Gamma, grain: str = "month") -> Gamma:
        if address.time_label:
            return Gamma(**{**asdict(address), "time_label": coarse_time(address.time_label, grain=grain)})
        return address
    def write_delta(self, address: Gamma, field: str, new_value: str, old_value: Optional[str] = None, source_id: str = "", reason: str = "", keep_history: bool = True, human: bool = False, identity: float = 1.0, grain: str = "month") -> Optional[Delta]:
        # identity=1.0 means the 0.20 gate stays open unless the caller passes a score.
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
    def write_is(self, address: Gamma, field: str, value: str, human: bool = False, identity: float = 1.0, grain: str = "month") -> Optional[str]:
        """Adopt into isolated IS. Does not append Δ. identity=1.0 leaves the gate open."""
        word = canon_word(field)
        text = str(value).strip()
        if not text:
            self.last_write = Write.NONE
            return None
        if word not in self.allowed_words():
            self.last_write = Write.UNKNOWN_WORD
            return None
        decision = gate(self.eta, identity, human)
        if decision == Write.NONE:
            self.last_write = Write.NONE
            return None
        address = self._prepare_address(address, grain=grain)
        line = f"{word}={text}"
        if decision == Write.HUMAN:
            item = (address, line)
            if item not in self._is_pending:
                self._is_pending.append(item)
            self.last_write = Write.HUMAN
            return None
        return self._adopt_is(address, line)
    def _adopt_is(self, address, line):
        key = address.key()
        bag = list(self._is.get(key, []))
        if line in bag:
            bag.remove(line)
        bag.append(line)
        self._is[key] = bag[-IS_MAX:]
        self._index_put(address)
        self.last_write = Write.IS
        return line
    def approve_is(self, index=-1):
        if not self._is_pending:
            return None
        address, line = self._is_pending.pop(index)
        return self._adopt_is(address, line)
    def reject_is(self, index=-1):
        if not self._is_pending:
            return None
        return self._is_pending.pop(index)
    def ingest(self, raw: Any, human: bool = False, identity: float = 1.0, grain: str = "month") -> Optional[dict]:
        """Only LLM write entry. Closed packet to γ index / Δ index / isolated IS."""
        pkt = parse_packet(raw)
        if pkt is None:
            self.last_write = Write.BAD_PACKET
            return None
        address = self._prepare_address(packet_gamma(pkt), grain=grain)
        out = {"gamma": address, "delta": [], "is": [], "dropped": [], "write": Write.NONE}
        for row in pkt.get("delta") or []:
            d = self.write_delta(
                address,
                row["field"],
                row["new_value"],
                old_value=row.get("old_value"),
                source_id=row.get("source_id", "llm"),
                reason=row.get("reason", ""),
                human=human,
                identity=identity,
                grain=grain,
            )
            if d is not None:
                out["delta"].append(d)
            else:
                out["dropped"].append({"kind": "delta", "field": row.get("field"), "write": self.last_write})
        for row in pkt.get("is") or []:
            line = self.write_is(
                address,
                row["field"],
                row["value"],
                human=human,
                identity=identity,
                grain=grain,
            )
            if line is not None:
                out["is"].append(line)
            else:
                out["dropped"].append({"kind": "is", "field": row.get("field"), "write": self.last_write})
        out["wrote"] = {"delta": len(out["delta"]), "is": len(out["is"])}
        if out["is"]:
            out["write"] = Write.IS
        elif out["delta"]:
            out["write"] = Write.DELTA
        elif out["dropped"]:
            out["write"] = self.last_write
        else:
            self.last_write = Write.NONE
            out["write"] = Write.NONE
        return out
    def pending(self):
        return list(self._pending)
    def pending_is(self):
        return list(self._is_pending)
    def approve_pending(self, index=-1, keep_history=True):
        if not self._pending:
            return None
        address, d = self._pending.pop(index)
        return self._commit(address, d, keep_history=keep_history)
    def reject_pending(self, index=-1):
        if not self._pending:
            return None
        return self._pending.pop(index)
    def _addresses(self):
        # _index is the address set. IS-only γ lives here too.
        seen = []
        for bag in self._index.values():
            for g in bag:
                if g not in seen:
                    seen.append(g)
        return seen
    def query_delta(self, filt, exact=True, grain="month"):
        filt = normalize_filt(filt, grain=grain)
        return [(g, d) for g, d in self._deltas if g.matches(filt, exact=exact)]
    def query_gamma(self, filt: dict, exact: bool = True, grain: str = "month") -> list[Gamma]:
        filt = normalize_filt(filt, grain=grain)
        if "project" in filt and "topic" in filt and exact:
            cand = list(self._index.get(f"{filt['project']}::{filt['topic']}", []))
        elif "project" in filt and exact:
            cand = list(self._by_project.get(filt["project"], []))
        elif "topic" in filt and exact:
            cand = list(self._by_topic.get(filt["topic"], []))
        else:
            cand = self._addresses()
        out = []
        for g in cand:
            if g.matches(filt, exact=exact) and g not in out:
                out.append(g)
        return out
    def latest_at(self, filt, exact=True, grain="month"):
        # latest = append order on _deltas. timestamp is audit only.
        last = {}
        for _, d in self.query_delta(filt, exact=exact, grain=grain):
            last[d.field] = d
        return list(last.values())
    def latest(self, filt, word, exact=True, grain="month"):
        word = canon_word(word)
        found = [d for _, d in self.query_delta(filt, exact=exact, grain=grain) if d.field == word]
        return found[-1] if found else None
    def history(self, filt, word, exact=True, grain="month"):
        word = canon_word(word)
        return [d for _, d in self.query_delta(filt, exact=exact, grain=grain) if d.field == word]
    def lookup(self, word):
        word = canon_word(word)
        out = []
        for g, d in self._deltas:
            if d.field == word and g not in out:
                out.append(g)
        return out
    def is_lines(self, filt, exact=True, grain="month"):
        # isolated IS only. Δ latest is not copied here.
        # footnote: IS_MAX lives in _adopt_is. wide filters keep every matching address.
        filt = normalize_filt(filt, grain=grain)
        lines = []
        for key, bag in self._is.items():
            g = Gamma(**json.loads(key))
            if not g.matches(filt, exact=exact):
                continue
            for line in bag:
                if line not in lines:
                    lines.append(line)
        return lines
    def snapshot(self):
        return {
            "deltas": [{"gamma": asdict(g), "delta": asdict(d)} for g, d in self._deltas],
            "is": dict(self._is),
            "pending": [{"gamma": asdict(g), "delta": asdict(d)} for g, d in self._pending],
            "is_pending": [{"gamma": asdict(g), "line": line} for g, line in self._is_pending],
            "adopted": sorted(self._adopted),
        }
    def restore(self, snap):
        # snapshot is internal. extra keys and broken rows are dropped, not trusted.
        if not isinstance(snap, dict):
            return self
        deltas = []
        for row in snap.get("deltas") or []:
            if not isinstance(row, dict):
                continue
            g, d = _load_gamma(row.get("gamma")), _load_delta(row.get("delta"))
            if g is not None and d is not None:
                deltas.append((g, d))
        pending = []
        for row in snap.get("pending") or []:
            if not isinstance(row, dict):
                continue
            g, d = _load_gamma(row.get("gamma")), _load_delta(row.get("delta"))
            if g is not None and d is not None:
                pending.append((g, d))
        is_store = {}
        raw_is = snap.get("is") or {}
        if isinstance(raw_is, dict):
            for key, bag in raw_is.items():
                try:
                    parsed = json.loads(key) if isinstance(key, str) else None
                except (json.JSONDecodeError, TypeError):
                    parsed = None
                g = _load_gamma(parsed)
                if g is None or not isinstance(bag, list):
                    continue
                lines = [x for x in bag if isinstance(x, str) and x]
                if lines:
                    is_store[g.key()] = lines[-IS_MAX:]
        is_pending = []
        for row in snap.get("is_pending") or []:
            if not isinstance(row, dict):
                continue
            g = _load_gamma(row.get("gamma"))
            line = row.get("line")
            if g is not None and isinstance(line, str) and line:
                is_pending.append((g, line))
        adopted = set()
        for w in snap.get("adopted") or []:
            if isinstance(w, str) and w:
                adopted.add(canon_word(w))
        self._deltas = deltas
        self._pending = pending
        self._is = is_store
        self._is_pending = is_pending
        self._adopted = adopted
        self._index = defaultdict(list)
        self._by_project = defaultdict(list)
        self._by_topic = defaultdict(list)
        for g, _ in self._deltas:
            self._index_put(g)
        for key in self._is:
            self._index_put(Gamma(**json.loads(key)))
        for g, _ in self._pending + self._is_pending:
            self._index_put(g)
        return self
    def render(self, user, filt, exact=True, grain="month"):
        filt = normalize_filt(filt, grain=grain)
        inn = self.inner
        if not inn.intact():
            bind = "核の整合性が壊れている。生成するな。"
        elif self.eta.high():
            bind = "偏差が大きい。基準へ戻せ。今の住所の外を埋めつな。核は書き換えるな。"
        else:
            bind = "基準に従って短く。更新と核を混ぜるな。核は変えるな。"
        if self._pending or self._is_pending:
            bind = f"{bind} pending Δ={len(self._pending)} IS={len(self._is_pending)}"
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

def make_test_capsule(name: str = "テスト体", tone: str = "簡潔", center: str = "中心軸", values: tuple[str, ...] = ("不変",), facts: tuple[BetaFact, ...] = ()) -> Capsule:
    return Capsule(Inner(Alpha(), Beta(name=name, tone=tone, center=center, values=values), facts=facts))
