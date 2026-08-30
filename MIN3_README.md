# AXIOM min3（作業線）

min2 を残したうえで、γ を3軸に落とした版。金型は `axiom_min.py`。

- γ: `time_label` + `project` + `topic`（住所。記憶ではない）
- Δ: 課題 / 改善点 / 結論 / 立場 / 状態（更新だけ）
- IS: Δ から隔離した採用リスト。最大3行。facts は αβ 側
- Gate: 生成文は見ない。`NONE` は捨て、`HUMAN` は pending、η は bind のみ
- LLM 書き込み: 閉じたパケット `{gamma, delta, is}` のみ。自由文は捨てる

```bash
python3 -m unittest test_axiom_min3.py
python3 phase3_gamma_history.py
```

latest は append 順。`timestamp` は監査用。index は `project::topic` に加え project / topic 単独バケツ。正確な判定は `Gamma.matches`。`identity` の省略値は 1.0 なので、0.20 ゲートを使うなら呼び出し側が点数を渡す。

`exact=True` は γ 3軸の全指定を要求しない。フィルタに書いた軸だけ完全一致し、書いていない軸はワイルドカードである。`{"project": "AXIOM"}` は同プロジェクトの全 topic に当たる。部分文字列の探索は `exact=False` に限る。

LLM から index へは次だけ通る。

```json
{
  "gamma": {"time_label": "2026-08", "project": "AXIOM", "topic": "Capsule"},
  "delta": [{"field": "状態", "new_value": "本筋"}],
  "is": [{"field": "結論", "value": "隔離"}]
}
```

`delta` はイベント流。`is` は可視3行。片方だけ送ってよい。未知キーと自由文は `bad_packet`。行単位の失敗は `ingest()["dropped"]`。

住所一覧 `query_gamma` は `_index` 基準。IS だけの γ も残る。query の `time_label` は write と同じ grain で粗くする。IS_MAX は住所ごとの採用上限であり、render の窓でもある。
`snapshot` / `restore` はメモリ状態の出し入れだけ。核は別。
