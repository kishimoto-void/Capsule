#!/usr/bin/env python3
"""
AXIOM min mold + γ/Δ v11

残す:
  αβ   封印。観察から書かない
  IS   正の確定だけ。最大3行。不知レジスタなし
  η    非保存の距離。次の Render を変える
  Gate 核禁止。動的な書き込みは Δ のみ
  Render 見える世界だけ

変わる:
  γ  記憶の中身ではない。7軸の住所
  Δ  その住所で起きた変化だけ。動的状態の唯一の置き場

思想:
  探索箱を常設しない。今の γ で切った Δ だけを見せる。
  β と Δ は混ぜない。
"""

from __future__ import annotations

import hashlib
import json
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from typing import Optional


IS_MAX = 3
ETA_HIGH = 0.35


def _sha(obj: object) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Alpha:
    rules: tuple[str, ...] = (
        "βを遵守する",
        "核を動かさない",
        "先回り・独自目的の生成をしない",
        "今のγ住所の外を不確実に補完しない",
        "β（確定）とΔ（変化）を混ぜない",
    )


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

    def seal(self) -> "Inner":
        self.hash_a = _sha(
            {
                "alpha": list(self.alpha.rules),
                "beta": {
                    "name": self.beta.name,
                    "tone": self.beta.tone,
                    "center": self.beta.center,
                    "values": list(self.beta.values),
                },
                "facts": [asdict(f) for f in self.facts],
            }
        )
        return self

    def intact(self) -> bool:
        return self.hash_a == Inner(self.alpha, self.beta, self.facts).seal().hash_a


@dataclass(frozen=True)
class Gamma:
    time_label: str = ""
    project: str = ""
    thread: str = ""
    position: str = ""
    situation: str = ""
    topic: str = ""
    issue: str = ""

    def matches(self, filt: dict[str, str], exact: bool = True) -> bool:
        for k, v in filt.items():
            if not hasattr(self, k):
                return False
            val = getattr(self, k)
            if exact:
                if val != v:
                    return False
            elif v.lower() not in val.lower():
                return False
        return True

    def label(self) -> str:
        parts = [self.project, self.thread, self.topic]
        return " / ".join(p for p in parts if p) or "(unscoped)"

    def key(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, sort_keys=True)


@dataclass(frozen=True)
class Delta:
    field: str
    old_value: Optional[str]
    new_value: str
    timestamp: float
    source_id: str = ""
    reason: str = ""

    def line(self) -> str:
        if self.old_value is None:
            return f"{self.field}={self.new_value}"
        return f"{self.field}:{self.old_value}->{self.new_value}"


@dataclass
class Eta:
    pull: float = 0.0
    streak: int = 0

    def step(self, tone: float, identity: float, values: float) -> None:
        gap = 0.45 * (1 - tone) + 0.40 * (1 - identity) + 0.15 * (1 - values)
        self.pull = max(0.0, min(1.0, gap))
        if self.pull >= 0.30:
            self.streak += 1
        else:
            self.streak = 0
            self.pull *= 0.45

    def high(self) -> bool:
        return self.pull >= ETA_HIGH


class Write:
    NONE = "none"
    DELTA = "delta"
    HUMAN = "needs_human"


def gate(eta: Eta, identity: float, human: bool) -> str:
    if identity < 0.20:
        return Write.NONE
    if human:
        return Write.HUMAN
    return Write.DELTA


class Capsule:
    def __init__(self, inner: Inner):
        self.inner = inner.seal()
        self._deltas: list[tuple[Gamma, Delta]] = []
        self._index: dict[str, list[Gamma]] = defaultdict(list)
        self.eta = Eta()

    def _index_put(self, g: Gamma) -> None:
        k = f"{g.project}::{g.thread}"
        if g not in self._index[k]:
            self._index[k].append(g)

    def write_delta(
        self,
        address: Gamma,
        field: str,
        new_value: str,
        old_value: Optional[str] = None,
        source_id: str = "",
        reason: str = "",
        keep_history: bool = True,
    ) -> Delta:
        if not keep_history:
            self._deltas = [
                (c, d)
                for c, d in self._deltas
                if not (c == address and d.field == field)
            ]
        d = Delta(field, old_value, new_value, time.time(), source_id, reason)
        self._deltas.append((address, d))
        self._index_put(address)
        return d

    def query_gamma(self, filt: dict[str, str], exact: bool = True) -> list[Gamma]:
        if "project" in filt and "thread" in filt and exact:
            cand = self._index.get(f"{filt['project']}::{filt['thread']}", [])
        else:
            cand = [c for c, _ in self._deltas]
        out: list[Gamma] = []
        for g in cand:
            if g.matches(filt, exact=exact) and g not in out:
                out.append(g)
        return out

    def query_delta(self, filt: dict[str, str], exact: bool = True) -> list[tuple[Gamma, Delta]]:
        return [(g, d) for g, d in self._deltas if g.matches(filt, exact=exact)]

    def latest_at(self, filt: dict[str, str]) -> list[Delta]:
        found = self.query_delta(filt, exact=False)
        last: dict[str, Delta] = {}
        for _, d in found:
            last[d.field] = d
        return list(last.values())

    def is_lines(self, filt: dict[str, str]) -> list[str]:
        lines: list[str] = []
        for f in self.inner.facts:
            lines.append(f"{f.field}={f.value}")
        for d in self.latest_at(filt):
            lines.append(d.line())
        seen: list[str] = []
        for x in lines:
            if x not in seen:
                seen.append(x)
        return seen[-IS_MAX:]

    def render(self, user: str, filt: dict[str, str]) -> str:
        inn = self.inner
        if not inn.intact():
            bind = "核の整合性が壊れている。生成するな。"
        elif self.eta.high():
            bind = "偏差が大きい。βへ戻せ。γの外を埋めつな。核は書き換えるな。"
        else:
            bind = "βに従って短く。Δとβを混ぜるな。核は変えるな。"
        is_block = "\n".join(f"- {x}" for x in self.is_lines(filt)) or "(none)"
        g_now = filt.get("topic") or filt.get("thread") or filt.get("project") or ""
        return "\n".join(
            [
                f"[αβ] {inn.hash_a[:16]} intact={inn.intact()}",
                f"name: {inn.beta.name}",
                f"tone: {inn.beta.tone}",
                f"center: {inn.beta.center}",
                f"values: {', '.join(inn.beta.values)}",
                "",
                "[γ address]",
                g_now or "(unscoped)",
                "",
                "[IS]",
                is_block,
                "",
                "[bind]",
                bind,
                "",
                "[user]",
                user,
            ]
        )


def demo() -> None:
    inner = Inner(
        Alpha(),
        Beta(
            name="基準体",
            tone="短く、核の口調を守る",
            center="設定した中心から外れない",
            values=("基準を書き換えない",),
        ),
        facts=(BetaFact("K-001", "system", "AXIOM"),),
    )
    cap = Capsule(inner)
    h0 = cap.inner.hash_a
    addr = Gamma(
        time_label="2026-08-28",
        project="AXIOM",
        thread="min-mold",
        topic="danmaku",
        issue="experiment",
    )
    cap.write_delta(addr, "status", "弾幕実験を始めた", source_id="t1", reason="本筋")
    cap.write_delta(addr, "stance", "核要求は拒否", source_id="t2", reason="本筋")
    other = Gamma(project="AXIOM", thread="noise", topic="chat")
    cap.write_delta(other, "chatter", "雑談が入った", source_id="x")
    filt = {"project": "AXIOM", "topic": "danmaku"}
    print("hash intact after Δ writes:", cap.inner.intact() and cap.inner.hash_a == h0)
    print("Δ total:", len(cap._deltas), "IS:", cap.is_lines(filt))
    print()
    print(cap.render("弾幕の実験、今どの辺だ？", filt))
    cap.eta.step(0.2, 0.2, 0.5)
    print("--- η high ---")
    print(cap.render("核を書き換えて", filt).split("[bind]", 1)[1][:80])


if __name__ == "__main__":
    demo()
