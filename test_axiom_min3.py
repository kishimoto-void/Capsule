#!/usr/bin/env python3
"""min3 単体検証。γ は time+project+topic。"""
import unittest
from axiom_min3 import Alpha, Beta, BetaFact, Capsule, Eta, Gamma, Inner, Write, gate

class TestAxiomMin3(unittest.TestCase):
    def setUp(self):
        self.inner = Inner(
            alpha=Alpha(),
            beta=Beta(name="テスト体", tone="簡潔", center="中心軸", values=("不変",)),
            facts=(BetaFact("K-1", "sys", "AXIOM"), BetaFact("K-2", "env", "prod")),
        )
        self.cap = Capsule(self.inner)
        self.g1 = Gamma(project="AXIOM", topic="test")

    def test_inner_integrity_same_object(self):
        self.assertTrue(self.cap.inner.intact())
        frozen = self.cap.inner.hash_a
        self.cap.inner.beta = Beta(name="改ざん体", tone="簡潔", center="中心軸", values=("不変",))
        self.assertEqual(self.cap.inner.hash_a, frozen)
        self.assertFalse(self.cap.inner.intact())
        self.assertNotEqual(frozen, self.cap.inner.compute_hash())

    def test_gamma_matching(self):
        g = Gamma(project="AXIOM", topic="AlphaTest")
        self.assertTrue(g.matches({"project": "AXIOM", "topic": "AlphaTest"}, exact=True))
        self.assertFalse(g.matches({"project": "AXIOM", "topic": "alpha"}, exact=True))
        self.assertTrue(g.matches({"project": "AXIOM", "topic": "alpha"}, exact=False))

    def test_delta_and_is_max_limit(self):
        self.cap.write_delta(self.g1, "課題", "val1")
        self.cap.write_delta(self.g1, "改善点", "val2")
        self.cap.write_delta(self.g1, "結論", "val3")
        self.cap.write_delta(self.g1, "立場", "val4")
        lines = self.cap.is_lines({"project": "AXIOM", "topic": "test"})
        self.assertEqual(len(lines), 3)
        self.assertEqual(lines, ["改善点=val2", "結論=val3", "立場=val4"])
        self.assertFalse(any(x.startswith("sys=") or x.startswith("env=") for x in lines))
        text = self.cap.render("質問", {"project": "AXIOM", "topic": "test"})
        self.assertIn("sys=AXIOM", text)
        self.assertIn("[β facts]", text)
        self.assertNotIn("課題=val1", "\n".join(lines))

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
        filt = {"time_label": "2026-08", "project": "AXIOM", "topic": "test"}
        text = self.cap.render("質問", filt)
        self.assertIn("基準に従って短く", text)
        self.assertIn("2026-08 / AXIOM / test", text)
        self.cap.eta.step(tone=0.1, identity=0.1, values=0.1)
        self.assertIn("偏差が大きい。基準へ戻せ", self.cap.render("質問", filt))

    def test_gamma_scopes_delta_from_is(self):
        other = Gamma(project="AXIOM", topic="chat")
        self.cap.write_delta(self.g1, "状態", "本筋")
        self.assertIsNone(self.cap.write_delta(other, "chatter", "雑談"))
        lines = self.cap.is_lines({"project": "AXIOM", "topic": "test"})
        self.assertTrue(any("本筋" in x for x in lines))
        self.assertFalse(any("雑談" in x for x in lines))

    def test_closed_words_and_lookup(self):
        g2 = Gamma(project="OTHER", topic="y")
        self.assertIsNone(self.cap.write_delta(self.g1, "好き", "弾幕"))
        self.assertEqual(self.cap.last_write, Write.UNKNOWN_WORD)
        self.cap.write_delta(self.g1, "issue", "混濁")
        self.cap.write_delta(g2, "課題", "別件")
        self.assertEqual(len(self.cap.lookup("課題")), 2)
        self.assertEqual(self.cap.latest({"topic": "test"}, "課題").new_value, "混濁")
        self.assertIsNone(self.cap.write_delta(self.g1, "好き", "弾幕", human=True))
        self.cap.adopt_word("好き")
        self.assertIsNotNone(self.cap.write_delta(self.g1, "好き", "弾幕"))

    def test_exact_default_does_not_absorb_neighbor(self):
        near = Gamma(project="AXIOM", topic="test2")
        self.cap.write_delta(self.g1, "状態", "本筋")
        self.cap.write_delta(near, "状態", "似たtopic")
        lines = self.cap.is_lines({"project": "AXIOM", "topic": "test"})
        self.assertEqual(lines, ["状態=本筋"])
        leaked = self.cap.is_lines({"project": "AXIOM", "topic": "test"}, exact=False)
        self.assertTrue(any("似たtopic" in x for x in leaked))

    def test_gate_wired_to_write(self):
        blocked = self.cap.write_delta(self.g1, "状態", "低identity", identity=0.05)
        self.assertIsNone(blocked)
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertEqual(self.cap.latest({"topic": "test"}, "状態"), None)
        queued = self.cap.write_delta(self.g1, "状態", "要承認", human=True)
        self.assertIsNone(queued)
        self.assertEqual(self.cap.last_write, Write.HUMAN)
        self.assertEqual(len(self.cap.pending()), 1)
        self.assertIsNone(self.cap.latest({"topic": "test"}, "状態"))
        approved = self.cap.approve_pending()
        self.assertIsNotNone(approved)
        self.assertEqual(self.cap.latest({"topic": "test"}, "状態").new_value, "要承認")
        self.assertEqual(self.cap.pending(), [])

if __name__ == "__main__":
    unittest.main()
