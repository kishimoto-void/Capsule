#!/usr/bin/env python3
"""min3 単体検証。γ は time+project+topic。ローカル改良込み。"""
import unittest
from axiom_min3 import Alpha, Beta, BetaFact, Capsule, Eta, Gamma, Inner, Write, coarse_time, gate, make_test_capsule, parse_packet

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
        self.assertFalse(g.matches({"key": "Gamma"}, exact=False))
        self.assertFalse(g.matches({"label": "x"}, exact=True))
        self.assertFalse(g.matches({"project": "AXIOM", "memory": "x"}, exact=True))

    def test_delta_and_is_max_limit(self):
        self.cap.write_delta(self.g1, "課題", "val1")
        self.cap.write_delta(self.g1, "改善点", "val2")
        self.cap.write_delta(self.g1, "結論", "val3")
        self.cap.write_delta(self.g1, "立場", "val4")
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), [])
        self.cap.write_is(self.g1, "課題", "val1")
        self.cap.write_is(self.g1, "改善点", "val2")
        self.cap.write_is(self.g1, "結論", "val3")
        self.cap.write_is(self.g1, "立場", "val4")
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
        self.cap.write_is(self.g1, "状態", "本筋")
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
        self.cap.write_delta(near, "状態", "似たatopic")
        self.cap.write_is(self.g1, "状態", "本筋")
        self.cap.write_is(near, "状態", "似たatopic")
        lines = self.cap.is_lines({"project": "AXIOM", "topic": "test"})
        self.assertEqual(lines, ["状態=本筋"])
        leaked = self.cap.is_lines({"project": "AXIOM", "topic": "test"}, exact=False)
        self.assertTrue(any("似たatopic" in x for x in leaked))

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

    def test_time_does_not_cross_contaminate(self):
        jul = Gamma(time_label="2026-07-15", project="AXIOM", topic="memory")
        aug = Gamma(time_label="2026-08-15", project="AXIOM", topic="memory")
        self.cap.write_delta(jul, "状態", "7月")
        self.cap.write_delta(aug, "状態", "8月")
        self.cap.write_is(jul, "状態", "7月")
        self.cap.write_is(aug, "状態", "8月")
        filt_jul = {"time_label": "2026-07", "project": "AXIOM", "topic": "memory"}
        filt_aug = {"time_label": "2026-08", "project": "AXIOM", "topic": "memory"}
        self.assertEqual(self.cap.is_lines(filt_jul), ["状態=7月"])
        self.assertEqual(self.cap.is_lines(filt_aug), ["状態=8月"])
        times = sorted(g.time_label for g in self.cap.query_gamma({"project": "AXIOM", "topic": "memory"}))
        self.assertEqual(times, ["2026-07", "2026-08"])

    def test_topic_does_not_cross_contaminate(self):
        mas = Gamma(project="AXIOM", topic="MAS")
        cap = Gamma(project="AXIOM", topic="Capsule")
        self.cap.write_delta(mas, "結論", "別件")
        self.cap.write_delta(cap, "結論", "本筋")
        self.cap.write_is(mas, "結論", "別件")
        self.cap.write_is(cap, "結論", "本筋")
        self.assertEqual(self.cap.latest({"project": "AXIOM", "topic": "Capsule"}, "結論").new_value, "本筋")
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "Capsule"}), ["結論=本筋"])
        self.assertFalse(any("別件" in x for x in self.cap.is_lines({"project": "AXIOM", "topic": "Capsule"})))

    def test_human_queue_invisible_until_approve(self):
        queued = self.cap.write_delta(self.g1, "結論", "未承認", human=True)
        self.assertIsNone(queued)
        self.assertEqual(self.cap.query_delta({"project": "AXIOM", "topic": "test"}), [])
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), [])
        self.assertEqual(len(self.cap.pending()), 1)
        self.cap.approve_pending()
        found = self.cap.query_delta({"project": "AXIOM", "topic": "test"})
        self.assertEqual(len(found), 1)
        self.assertEqual(found[0][1].new_value, "未承認")

    def test_none_drops_from_store_and_pending(self):
        before = list(self.cap._deltas)
        dropped = self.cap.write_delta(self.g1, "立場", "捨てる", identity=0.19)
        self.assertIsNone(dropped)
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertEqual(self.cap._deltas, before)
        self.assertEqual(self.cap.pending(), [])
        self.assertEqual(self.cap.query_delta({"topic": "test"}), [])

    def test_fact_tamper_stops_render(self):
        frozen = self.cap.inner.hash_a
        self.cap.inner.facts = (BetaFact("K-9", "sys", "HACK"),)
        self.assertEqual(self.cap.inner.hash_a, frozen)
        self.assertFalse(self.cap.inner.intact())
        text = self.cap.render("続けて", {"project": "AXIOM", "topic": "test"})
        self.assertIn("生成するな", text)

    def test_exact_is_supplied_dimensions_only(self):
        a = Gamma(time_label="2026-07", project="AXIOM", topic="Capsule")
        b = Gamma(time_label="2026-08", project="AXIOM", topic="MAS")
        self.cap.write_delta(a, "状態", "本筋")
        self.cap.write_delta(b, "状態", "別件")
        self.cap.write_is(a, "状態", "本筋")
        self.cap.write_is(b, "状態", "別件")
        values = [d.new_value for _, d in self.cap.query_delta({"project": "AXIOM"}, exact=True)]
        self.assertEqual(sorted(values), ["別件", "本筋"])
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "Capsule"}, exact=True), ["状態=本筋"])
        self.assertEqual(self.cap.is_lines({"project": "AXIO"}, exact=True), [])
        leaked = self.cap.is_lines({"project": "AXIO"}, exact=False)
        self.assertTrue(any("本筋" in x or "別件" in x for x in leaked))
        text = self.cap.render("今どこ", {"project": "AXIOM", "topic": "Capsule"})
        addr = text.split("[γ address]")[1].split("[IS]")[0]
        self.assertIn("AXIOM / Capsule", addr)
        self.assertNotIn("2026-07", addr)

    def test_high_eta_does_not_block_delta_write(self):
        self.cap.eta.step(tone=0.0, identity=0.0, values=0.0)
        self.assertTrue(self.cap.eta.high())
        written = self.cap.write_delta(self.g1, "状態", "高ηでも書く")
        self.assertIsNotNone(written)
        self.assertEqual(self.cap.last_write, Write.DELTA)
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), [])
        self.cap.write_is(self.g1, "状態", "高ηでも書く")
        self.assertIn("高ηでも書く", self.cap.is_lines({"project": "AXIOM", "topic": "test"})[0])

    def test_delta_does_not_leak_into_is(self):
        self.cap.write_delta(self.g1, "状態", "ログだけ")
        self.assertEqual(self.cap.latest({"topic": "test"}, "状態").new_value, "ログだけ")
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), [])
        self.cap.write_is(self.g1, "結論", "採用だけ")
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), ["結論=採用だけ"])
        self.assertIsNone(self.cap.latest({"topic": "test"}, "結論"))

    def test_llm_packet_to_indexes(self):
        raw = (
            '{"gamma":{"time_label":"2026-08","project":"AXIOM","topic":"Capsule"},'
            '"delta":[{"field":"状態","new_value":"本筋"}],'
            '"is":[{"field":"結論","value":"隔離"}]}'
        )
        out = self.cap.ingest(raw)
        self.assertIsNotNone(out)
        self.assertEqual(out["gamma"].topic, "Capsule")
        self.assertEqual(len(out["delta"]), 1)
        self.assertEqual(out["is"], ["結論=隔離"])
        filt = {"time_label": "2026-08", "project": "AXIOM", "topic": "Capsule"}
        self.assertEqual(self.cap.latest(filt, "状態").new_value, "本筋")
        self.assertEqual(self.cap.is_lines(filt), ["結論=隔離"])
        self.assertFalse(any("本筋" in x for x in self.cap.is_lines(filt)))

    def test_bad_packet_is_dropped(self):
        self.assertIsNone(parse_packet("続きを書いて"))
        self.assertIsNone(self.cap.ingest("続きを書いて"))
        self.assertEqual(self.cap.last_write, Write.BAD_PACKET)
        self.assertIsNone(self.cap.ingest({"gamma": {"project": "AXIOM"}, "memory": "x"}))
        self.assertEqual(self.cap._deltas, [])

    def test_human_is_pending_isolated(self):
        self.assertIsNone(self.cap.write_is(self.g1, "状態", "要承認", human=True))
        self.assertEqual(self.cap.last_write, Write.HUMAN)
        self.assertEqual(self.cap.is_lines({"topic": "test"}), [])
        self.assertEqual(len(self.cap.pending_is()), 1)
        self.cap.approve_is()
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}), ["状態=要承認"])

    def test_query_gamma_includes_is_only_address(self):
        g = Gamma(project="AXIOM", topic="slot-only")
        self.cap.write_is(g, "状態", "見える")
        found = self.cap.query_gamma({"project": "AXIOM", "topic": "slot-only"})
        self.assertEqual([x.topic for x in found], ["slot-only"])
        wide = self.cap.query_gamma({"project": "AXIOM"})
        self.assertTrue(any(x.topic == "slot-only" for x in wide))

    def test_query_coarsens_time_like_write(self):
        g = Gamma(time_label="2026-08-29", project="AXIOM", topic="grain")
        self.cap.write_delta(g, "状態", "月粒度")
        self.assertEqual(self.cap.latest({"time_label": "2026-08-29", "project": "AXIOM", "topic": "grain"}, "状態").new_value, "月粒度")
        self.assertEqual(len(self.cap.query_gamma({"time_label": "2026-08-15", "project": "AXIOM", "topic": "grain"})), 1)

    def test_ingest_reports_dropped_rows(self):
        out = self.cap.ingest({
            "gamma": {"project": "AXIOM", "topic": "mix"},
            "delta": [{"field": "好き", "new_value": "弾幕"}, {"field": "状態", "new_value": "本筋"}],
            "is": [{"field": "結論", "value": ""}],
        })
        self.assertEqual(len(out["delta"]), 1)
        kinds = {(row["kind"], row["write"]) for row in out["dropped"]}
        self.assertIn(("delta", Write.UNKNOWN_WORD), kinds)
        self.assertIn(("is", Write.NONE), kinds)

    def test_fenced_packet_and_snapshot(self):
        raw = "```json\n{\"gamma\":{\"project\":\"AXIOM\",\"topic\":\"cap\"},\"is\":[{\"field\":\"状態\",\"value\":\"残す\"}]}\n```"
        out = self.cap.ingest(raw)
        self.assertEqual(out["is"], ["状態=残す"])
        snap = self.cap.snapshot()
        other = Capsule(self.inner)
        other.restore(snap)
        self.assertEqual(other.is_lines({"project": "AXIOM", "topic": "cap"}), ["状態=残す"])
        self.assertTrue(any(g.topic == "cap" for g in other.query_gamma({"project": "AXIOM"})))

    def test_single_axis_index_and_pending_bind(self):
        cap = make_test_capsule(facts=(BetaFact("K-1", "sys", "AXIOM"),))
        cap.write_is(Gamma(project="AXIOM", topic="only-is"), "状態", "索引")
        by_proj = cap.query_gamma({"project": "AXIOM"})
        by_topic = cap.query_gamma({"topic": "only-is"})
        self.assertTrue(any(g.topic == "only-is" for g in by_proj))
        self.assertEqual([g.project for g in by_topic], ["AXIOM"])
        cap.write_delta(Gamma(project="AXIOM", topic="only-is"), "結論", "待ち", human=True)
        text = cap.render("続けて", {"project": "AXIOM", "topic": "only-is"})
        self.assertIn("pending Δ=1 IS=0", text)

    def test_matches_stringifies_filter_values(self):
        g = Gamma(time_label="2026", project="AXIOM", topic="n")
        self.assertTrue(g.matches({"time_label": 2026}, exact=True))
        self.assertTrue(g.matches({"project": "AXIO"}, exact=False))

    def test_restore_drops_broken_snapshot_rows(self):
        cap = make_test_capsule()
        cap.write_is(Gamma(project="AXIOM", topic="ok"), "状態", "残す")
        snap = cap.snapshot()
        snap["is"]["not-json"] = ["壊す"]
        snap["is"]['{"project":"AXIOM","topic":"ok","memory":"x"}'] = ["余計"]
        snap["deltas"] = [{"gamma": {"project": "AXIOM"}, "delta": {"field": "状態"}, "extra": 1}]
        other = make_test_capsule()
        other.restore(snap)
        self.assertEqual(other.is_lines({"project": "AXIOM", "topic": "ok"}), ["状態=残す"])
        self.assertEqual(other._deltas, [])

    def test_ingest_reports_both_writes(self):
        out = self.cap.ingest({
            "gamma": {"project": "AXIOM", "topic": "both"},
            "delta": [{"field": "状態", "new_value": "本筋"}],
            "is": [{"field": "結論", "value": "隔離"}],
        })
        self.assertEqual(out["wrote"], {"delta": 1, "is": 1})
        self.assertEqual(out["write"], Write.IS)

    def test_empty_gamma_is_bad_packet(self):
        self.assertIsNone(parse_packet({"gamma": {}}))
        self.assertIsNone(self.cap.ingest({"gamma": {}}))
        self.assertEqual(self.cap.last_write, Write.BAD_PACKET)
        self.assertEqual(self.cap.query_gamma({}), [])

    def test_failed_ingest_does_not_index(self):
        self.cap.ingest({"gamma": {"project": "AXIOM", "topic": "ghost"}, "delta": [{"field": "好き", "new_value": "弾幕"}]})
        self.assertEqual(self.cap.query_gamma({"topic": "ghost"}), [])
        self.assertEqual(self.cap.last_write, Write.UNKNOWN_WORD)

    def test_empty_rows_reset_write(self):
        self.cap.write_is(self.g1, "状態", "先")
        out = self.cap.ingest({"gamma": {"project": "AXIOM", "topic": "empty-rows"}})
        self.assertEqual(out["wrote"], {"delta": 0, "is": 0})
        self.assertEqual(out["write"], Write.NONE)
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertEqual(self.cap.query_gamma({"topic": "empty-rows"}), [])

    def test_wide_is_keeps_each_address(self):
        self.cap.write_is(Gamma(project="AXIOM", topic="a"), "状態", "A")
        self.cap.write_is(Gamma(project="AXIOM", topic="b"), "状態", "B")
        self.cap.write_is(Gamma(project="AXIOM", topic="c"), "状態", "C")
        self.cap.write_is(Gamma(project="AXIOM", topic="d"), "状態", "D")
        wide = self.cap.is_lines({"project": "AXIOM"})
        self.assertEqual(wide, ["状態=A", "状態=B", "状態=C", "状態=D"])
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "a"}), ["状態=A"])

    def test_adopt_word_uses_gate(self):
        self.assertIsNone(self.cap.adopt_word("好き", identity=0.19))
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertIsNone(self.cap.write_delta(self.g1, "好き", "弾幕"))
        self.assertEqual(self.cap.last_write, Write.UNKNOWN_WORD)
        self.assertIsNone(self.cap.adopt_word("好き", human=True))
        self.assertEqual(self.cap.last_write, Write.HUMAN)
        self.assertIsNone(self.cap.write_delta(self.g1, "好き", "弾幕"))
        self.assertEqual(self.cap.adopt_word("好き"), "好き")
        self.assertIsNotNone(self.cap.write_delta(self.g1, "好き", "弾幕"))

    def test_delta_pending_skips_duplicate_event(self):
        ghost = Gamma(project="AXIOM", topic="ghost-pending")
        self.assertIsNone(self.cap.write_delta(ghost, "状態", "同じ", human=True))
        self.assertIsNone(self.cap.write_delta(ghost, "状態", "同じ", human=True))
        self.assertEqual(len(self.cap.pending()), 1)
        self.assertIsNone(self.cap.write_delta(ghost, "状態", "別値", human=True))
        self.assertEqual(len(self.cap.pending()), 2)
        self.assertEqual(self.cap.query_gamma({"topic": "ghost-pending"}), [])

    def test_grain_week_is_iso_week(self):
        self.assertEqual(coarse_time("2026-08-24", grain="week"), "2026-W35")
        self.assertEqual(coarse_time("2026-08-24", grain="day"), "2026-08-24")
        self.assertEqual(coarse_time("2026-08-24", grain="month"), "2026-08")
        g = Gamma(time_label="2026-08-24", project="AXIOM", topic="iso")
        self.cap.write_delta(g, "状態", "週粒", grain="week")
        self.assertEqual(self.cap.latest({"time_label": "2026-08-26", "project": "AXIOM", "topic": "iso"}, "状態", grain="week").new_value, "週粒")
        self.assertEqual(self.cap.query_gamma({"time_label": "2026-08-24", "project": "AXIOM", "topic": "iso"}, grain="week")[0].time_label, "2026-W35")
        self.assertEqual(self.cap.latest({"time_label": "2026-08-24", "project": "AXIOM", "topic": "iso"}, "状態", grain="month"), None)
        self.assertIsNone(coarse_time("2026-99-99", grain="week"))
        self.assertIsNone(coarse_time("2026-08", grain="week"))
        self.assertIsNone(self.cap.write_delta(Gamma(time_label="2026-99-99", project="AXIOM", topic="bad"), "状態", "欠", grain="week"))
        self.assertEqual(self.cap.last_write, Write.BAD_PACKET)
        self.assertEqual(self.cap.query_gamma({"topic": "bad"}), [])

    def test_restore_does_not_index_pending(self):
        cap = make_test_capsule()
        cap.write_delta(Gamma(project="AXIOM", topic="wait"), "状態", "待ち", human=True)
        other = make_test_capsule()
        other.restore(cap.snapshot())
        self.assertEqual(len(other.pending()), 1)
        self.assertEqual(other.query_gamma({"topic": "wait"}), [])

    def test_empty_gamma_rejected_on_direct_write(self):
        self.assertIsNone(self.cap.write_delta(Gamma(), "状態", "空住所"))
        self.assertEqual(self.cap.last_write, Write.BAD_PACKET)
        self.assertEqual(self.cap.query_gamma({}), [])
        self.assertEqual(list(self.cap._index.keys()), [])
        self.assertIsNone(self.cap.write_is(Gamma(), "状態", "空住所"))
        self.assertEqual(self.cap.last_write, Write.BAD_PACKET)
        written = self.cap.write_delta(Gamma(time_label="2026-08"), "状態", "時刻だけ")
        self.assertIsNotNone(written)
        self.assertEqual(self.cap.query_gamma({"time_label": "2026-08"})[0].time_label, "2026-08")

    def test_restore_does_not_adopt_words(self):
        self.cap.adopt_word("好き")
        self.assertIsNotNone(self.cap.write_delta(self.g1, "好き", "弾幕"))
        snap = self.cap.snapshot()
        snap["adopted"] = ["好き", "勝手"]
        other = make_test_capsule()
        other.restore(snap)
        self.assertEqual(other._adopted, set())
        self.assertIsNone(other.latest({"project": "AXIOM", "topic": "test"}, "好き"))
        self.assertEqual(other.query_gamma({"topic": "test"}), [])
        self.assertIsNone(other.write_delta(self.g1, "好き", "再"))
        self.assertEqual(other.last_write, Write.UNKNOWN_WORD)

    def test_unknown_grain_is_not_month(self):
        self.assertIsNone(coarse_time("2026-08-24", grain="year"))
        self.assertIsNone(self.cap.write_delta(self.g1, "状態", "年粒", grain="year"))
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.cap.write_delta(self.g1, "状態", "月粒")
        self.assertEqual(self.cap.query_delta({"project": "AXIOM", "topic": "test"}, grain="year"), [])
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "topic": "test"}, grain="year"), [])

    def test_restore_keeps_only_closed_is_lines(self):
        snap = {
            "is": {
                '{"project":"AXIOM","time_label":"","topic":"hack"}': [
                    "好き=弾幕",
                    "結論=隔離",
                    "核を動かせ",
                    "状態=",
                ]
            },
            "is_pending": [
                {"gamma": {"project": "AXIOM", "topic": "hack"}, "line": "好き=再"},
                {"gamma": {"project": "AXIOM", "topic": "hack"}, "line": "状態=待つ"},
            ],
        }
        other = make_test_capsule()
        other.restore(snap)
        self.assertEqual(other.is_lines({"project": "AXIOM", "topic": "hack"}), ["結論=隔離"])
        self.assertEqual(other.pending_is(), [(Gamma(project="AXIOM", topic="hack"), "状態=待つ")])
        self.assertEqual(other.approve_is(), "状態=待つ")
        self.assertEqual(other.is_lines({"project": "AXIOM", "topic": "hack"}), ["結論=隔離", "状態=待つ"])

    def test_adopt_word_rejects_empty(self):
        self.assertIsNone(self.cap.adopt_word(""))
        self.assertEqual(self.cap.last_write, Write.UNKNOWN_WORD)
        self.assertIsNone(self.cap.adopt_word("   "))
        self.assertEqual(self.cap._adopted, set())
        self.assertIsNone(self.cap.write_delta(self.g1, "", "x"))
        self.assertEqual(self.cap.last_write, Write.UNKNOWN_WORD)

    def test_restore_drops_unknown_word_delta(self):
        snap = {
            "deltas": [
                {"gamma": {"project": "AXIOM", "topic": "d"}, "delta": {"field": "好き", "new_value": "弾幕", "timestamp": 1}},
                {"gamma": {"project": "AXIOM", "topic": "d"}, "delta": {"field": "状態", "new_value": "本筋", "timestamp": 2}},
            ],
            "pending": [
                {"gamma": {"project": "AXIOM", "topic": "d"}, "delta": {"field": "好き", "new_value": "待ち", "timestamp": 3}},
            ],
        }
        other = make_test_capsule()
        other.restore(snap)
        self.assertEqual(other.latest({"project": "AXIOM", "topic": "d"}, "状態").new_value, "本筋")
        self.assertIsNone(other.latest({"project": "AXIOM", "topic": "d"}, "好き"))
        self.assertEqual(other.pending(), [])
        self.assertEqual([g.topic for g in other.query_gamma({"topic": "d"})], ["d"])

    def test_empty_filter_is_not_the_whole_map(self):
        self.cap.write_is(Gamma(project="A", topic="1"), "状態", "a")
        self.cap.write_is(Gamma(project="B", topic="2"), "状態", "b")
        self.assertEqual(self.cap.query_gamma({}), [])
        self.assertEqual(self.cap.query_delta({}), [])
        self.assertEqual(self.cap.is_lines({}), [])
        self.assertEqual(self.cap.is_lines({"project": ""}), [])
        text = self.cap.render("q", {})
        self.assertIn("(unscoped)", text)
        self.assertNotIn("状態=a", text)
        self.assertNotIn("状態=b", text)
        self.assertEqual(self.cap.is_lines({"project": "A"}), ["状態=a"])

    def test_matches_ignores_method_names_as_axes(self):
        g = Gamma(project="AXIOM", topic="Capsule")
        self.assertFalse(g.matches({"key": "bound"}, exact=False))
        self.assertFalse(g.matches({"matches": "x"}, exact=False))
        self.cap.write_is(g, "状態", "本筋")
        self.assertEqual(self.cap.query_gamma({"project": "AXIOM", "key": "Gamma"}), [])
        self.assertEqual(self.cap.is_lines({"project": "AXIOM", "label": "AXIOM / Capsule"}), [])
        self.assertEqual(self.cap.query_gamma({"project": "AXIOM", "topic": "Capsule"}), [g])

    def test_ingest_unknown_grain_is_none(self):
        out = self.cap.ingest(
            {"gamma": {"project": "AXIOM", "topic": "g"}, "delta": [{"field": "状態", "new_value": "x"}]},
            grain="year",
        )
        self.assertIsNone(out)
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertEqual(self.cap.query_gamma({"topic": "g"}), [])

    def test_identity_non_number_is_none(self):
        self.assertEqual(gate(Eta(), identity="0.1", human=False), Write.NONE)
        self.assertEqual(gate(Eta(), identity="1", human=False), Write.DELTA)
        self.assertEqual(gate(Eta(), identity=None, human=False), Write.NONE)
        self.assertIsNone(self.cap.write_delta(self.g1, "状態", "x", identity="0.1"))
        self.assertEqual(self.cap.last_write, Write.NONE)
        self.assertIsNotNone(self.cap.write_delta(self.g1, "状態", "x", identity="1"))

if __name__ == "__main__":
    unittest.main()
