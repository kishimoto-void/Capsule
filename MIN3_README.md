# AXIOM min3（作業線）

min2 を残したうえで、γ を3軸に落とした版。金型は `axiom_min.py`。触らない。

- γ: `time_label` + `project` + `topic`
- Δ: 課題 / 改善点 / 結論 / 立場 / 状態
- IS: 正の確定だけ。最大3行。溢れたら先頭が落ちる（仕様）
- Gate: Δ 書き込みと未知語の拒否。生成文は見ない

```bash
python3 -m unittest test_axiom_min3.py
python3 phase3_gamma_history.py
```

Phase 2 の5問では min2 と min3 の F/核は同じ 0 だった。差が出るのは文字数ではなく、粗いフィルタ（min2 の thread だけ指定など）で住所が混ざるとき。
