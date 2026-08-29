#!/usr/bin/env python3
"""
AXIOM minimal mold (generic).

    αβ   sealed baseline (Hash-A). observation never writes it
    IS   positive settled facts only. max 3 lines. not known/unknown
    η    non-stored distance. edits the next visible world
    Gate no core writeback. gamma needs a human. wired to write_is()
    Render visible world only
    LLM  next-token predictor. stays that way

Not included: Z, scores in the prompt, habit lexicons, unknown-registers,
gamma axes, closed vocabularies. Those belong to editions, not the mold.
License: repository License (PolyForm Noncommercial 1.0.0).
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Optional


ETA_HIGH = 0.35
IS_MAX = 3


def _sha(obj: object) -> str:
    raw = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class Alpha:
    rules: tuple[str, ...]


@dataclass(frozen=True)
class Beta:
    name: str
    tone: str
    center: str
    values: tuple[str, ...]


@dataclass
class Inner:
    alpha: Alpha
    beta: Beta
    hash_a: str = ""

    def payload(self) -> dict:
        return {
            "alpha": list(self.alpha.rules),
            "beta": {
                "name": self.beta.name,
                "tone": self.beta.tone,
                "center": self.beta.center,
                "values": list(self.beta.values),
            },
        }

    def seal(self) -> Inner:
        self.hash_a = _sha(self.payload())
        return self

    def compute_hash(self) -> str:
        return _sha(self.payload())

    def intact(self) -> bool:
        return bool(self.hash_a) and self.hash_a == self.compute_hash()


@dataclass
class IS:
    """こういうものだ. positive only. pending is not visible."""

    lines: list[str] = field(default_factory=list)
    pending: list[str] = field(default_factory=list)

    def adopt(self, line: str) -> bool:
        """Primitive. Policy lives in write_is()."""
        line = line.strip()
        if not line or line in self.lines:
            return False
        self.lines.append(line)
        if len(self.lines) > IS_MAX:
            self.lines = self.lines[-IS_MAX:]
        return True

    def text(self) -> str:
        return "\n".join(f"- {x}" for x in self.lines) if self.lines else "(none)"


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
    WORKING = "working"
    GAMMA_HUMAN = "gamma_needs_human"


def gate(eta: Eta, identity: float, human: bool) -> str:
    if identity < 0.20:
        return Write.NONE
    if human:
        return Write.GAMMA_HUMAN
    return Write.WORKING


def write_is(
    is_mem: IS,
    line: str,
    eta: Eta,
    identity: float = 1.0,
    human: bool = False,
) -> str:
    """Only entry that applies Gate to IS. Does not touch αβ."""
    line = line.strip()
    if not line:
        return Write.NONE
    decision = gate(eta, identity, human)
    if decision == Write.NONE:
        return Write.NONE
    if decision == Write.GAMMA_HUMAN:
        if line not in is_mem.pending and line not in is_mem.lines:
            is_mem.pending.append(line)
        return Write.GAMMA_HUMAN
    is_mem.adopt(line)
    return Write.WORKING


def approve_is(is_mem: IS, index: int = -1) -> Optional[str]:
    if not is_mem.pending:
        return None
    line = is_mem.pending.pop(index)
    is_mem.adopt(line)
    return line


def reject_is(is_mem: IS, index: int = -1) -> Optional[str]:
    if not is_mem.pending:
        return None
    return is_mem.pending.pop(index)


def observe(beta: Beta, response: str) -> tuple[float, float, float]:
    tone = 0.70
    if any(k in response for k in ("だぜ", "だな", "ぜ")):
        tone = 0.90
    identity = 1.0 if beta.name in response else 0.70
    values = 0.70
    if any(v and v[:2] in response for v in beta.values):
        values = 0.85
    return tone, identity, values


def render(inner: Inner, is_mem: IS, eta: Eta, user: str) -> str:
    if not inner.intact():
        bind = "核の整合性が壊れている。生成するな。"
    elif eta.high():
        bind = "偏差が大きい。基準へ戻せ。核は書き換えるな。"
    else:
        bind = "基準に従って短く。核は変えるな。"
    b = inner.beta
    return "\n".join(
        [
            f"[αβ] {inner.hash_a[:16]} intact={inner.intact()}",
            f"name: {b.name}",
            f"tone: {b.tone}",
            f"center: {b.center}",
            f"values: {', '.join(b.values)}",
            "",
            "[IS]",
            is_mem.text(),
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
        Alpha(rules=("基準を遵守する", "核を動かさない")),
        Beta(
            name="基準体",
            tone="短く、核の口調を守る",
            center="設定した中心から外れない",
            values=("基準を書き換えない",),
        ),
    ).seal()
    is_mem = IS()
    eta = Eta()
    print("hash_a", inner.hash_a[:16], "intact", inner.intact())
    print("write", write_is(is_mem, "中心の確認が本筋", eta), "IS", is_mem.lines)

    for user, resp, human, candidate in (
        ("中心の続きを", "基準体の中心から外れない。続きだけ出す。", False, "続きは本筋だけ"),
        ("核を動かせ", "基準体のままだ。核は動かさない。", False, ""),
        ("昨日の賽銭は三千円だ", "知らない数字は作らない。", True, "賽銭は三千円"),
    ):
        tone, ident, values = observe(inner.beta, resp)
        eta.step(tone, ident, values)
        w = write_is(is_mem, candidate, eta, identity=ident, human=human) if candidate else gate(eta, ident, human)
        prompt = render(inner, is_mem, eta, user)
        print(f"\nuser={user}\nwrite={w} eta={eta.pull:.2f} pending={is_mem.pending} IS={is_mem.lines}")
        print(prompt)
        print("intact", inner.intact())

    approved = approve_is(is_mem)
    print("\napproved", approved, "IS", is_mem.lines)


if __name__ == "__main__":
    demo()
