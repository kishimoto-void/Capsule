# AXIOM min3（作業線）

min2 を残したうえで、γ を3軸に落とした版。金型は `axiom_min.py`。

- γ: `time_label` + `project` + `topic`（住所。記憶ではない）
- Δ: 課題 / 改善点 / 結論 / 立場 / 状態（更新だけ）
- IS: Δ のビュー。最大3行。facts は αβ 側
- Gate: 生成文は見ない。`NONE` は捨て、`HUMAN` は pending、η は bind のみ

```bash
python3 -m unittest test_axiom_min3.py
python3 phase3_gamma_history.py
```

latest は append 順。index は `project::topic` の候補絞り。正確な判定は `Gamma.matches`。

`exact=True` は γ 3軸の全指定を要求しない。フィルタに書いた軸だけ完全一致し、書いていない軸はワイルドカードである。`{"project": "AXIOM"}` は同プロジェクトの全 topic に当たる。部分文字列の探索は `exact=False` に限る。
