#!/usr/bin/env python3
"""min2 単体検証。金型 axiom_min.py は触らない。"""

import unittest

from axiom_min2 import (
    Alpha,
    Beta,
    BetaFact,
    Capsule,
    Eta,
    Gamma,
    Inner,
    Write,
    gate,
)


class TestAxiomMin2(unittest.TestCase):
    def setUp(self):
        self.inner = Inner(
            alpha=Alpha(),
            beta=Beta(name="テスト体", tone="簡潔", center="中心軸", values=("不変",)),
            facts=(BetaFact("K-1", "sys", "AXIOM"), BetaFact("K-2", "env", "prod")),
        )
        self.cap = Capsule(self.inner)
        self.g1 = Gamma(project="AXIOM", thread="main", topic="test")

    def test_inner_integrity_same_object(self):
        self.assertTrue(self.cap.inner.intact())
        frozen = self.cap.inner.hash_a
        self.cap.inner.beta = Beta(name="改ざん体", tone="簡潔", center="中心軸", values=("不変",))
        self.assertEqual(self.cap.inner.hash_a, frozen)
        self.assertFalse(self.cap.inner.intact())
        self.assertNotEqual(frozen, self.cap.inner.compute_hash())

    def test_gamma_matching(self):
        g = Gamma(project="AXIOM", thread="main", topic="AlphaTest")
        self.assertTrue(g.matches({"project": "AXIOM", "thread": "main"}, exact=True))
        self.assertFalse(g.matches({"project": "AXIOM", "topic": "alpha"}, exact=True))
        self.assertTrue(g.matches({"project": "AXIOM", "topic": "alpha"}, exact=False))

    def test_delta_and_is_max_limit(self):
        self.cap.write_delta(self.g1, "field1", "val1")
        self.cap.write_delta(self.g1, "field2", "val2")
        lines = self.cap.is_lines({"project": "AXIOM"})
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines, ["env=prod", "field1=val1", "field2=val2"])

    def test_eta_high_threshold(self):
        self.assertFalse(self.cap.eta.high())
        self.cap.eta.step(tone=0.2, identity=0.2, values=0.5)
        self.assertTrue(self.cap.eta.high())

    def test_gate_logic(self):
        eta = Eta()
        self.assertEqual(gate(eta, identity=0.1, human=False), Write.NONE)
        self.assertEqual(gate(eta, identity=0.5, human=True), Write.HUMAN)
        self.assertEqual(gate(eta, identity=0.5, human=False), Write.DELTA)

    def test_render_bind_switch(self):
        filt = {"project": "AXIOM"}
        self.assertIn("βに従って短く", self.cap.render("質問", filt))
        self.cap.eta.step(tone=0.1, identity=0.1, values=0.1)
        self.assertIn("偏差が大きい。βへ戻せ", self.cap.render("質問", filt))

    def test_gamma_scopes_delta_from_is(self):
        other = Gamma(project="AXIOM", thread="noise", topic="chat")
        self.cap.write_delta(self.g1, "status", "本筋")
        self.cap.write_delta(other, "chatter", "雑談")
        lines = self.cap.is_lines({"project": "AXIOM", "topic": "test"})
        self.assertTrue(any("本筋" in x for x in lines))
        self.assertFalse(any("雑談" in x for x in lines))


if __name__ == "__main__":
    unittest.main()
