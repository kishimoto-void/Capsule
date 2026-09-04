# AXIOM min3（作業線）

min2 を残したうえで、γ を3軸に落とした版。金型は `axiom_min.py`。

- γ: `time_label` + `project` + `topic`（住所。記憶ではない）
- Δ: 課題 / 改善点 / 結論 / 立場 / 状態（更新だけ）
- IS: Δ から隔離した採用リスト。最大3行。facts は αβ 側
- IS は語ごとに上書き。同じ語の旧行はスロットを食わない
- 溢れたときはピン以外の最古を落とす。ピンは `状態`。全部ピンなら最古
- Gate: 生成文は見ない。`NONE` は捨て、`HUMAN` は pending、η は bind のみ
- LLM 書き込み: 閉じたパケット `{gamma, delta, is}` のみ。自由文は捨てる

```bash
python3 -m unittest test_axiom_min3.py
python3 phase3_gamma_history.py
```

latest は append 順。`timestamp` は監査用。index は `project::topic` に加え project / topic 単独バケツ。正確な判定は `Gamma.matches`。`identity` の省略値は 1.0 なので、0.20 ゲートを使うなら呼び出し側が点数を渡す。

`exact=True` は γ 3軸の全指定を要求しない。フィルタに書いた軸だけ完全一致し、書いていない軸はワイルドカードである。`{"project": "AXIOM"}` は同プロジェクトの全 topic に当たる。部分文字列の探索は `exact=False` に限る。
