# AXIOM Capsule

LLM の外に着ける参照境界。知能ではない。

空白を埋める装置ではない。そのターンで空白を参照不能にする着脱部品である。

作業線は **min3**（`axiom_min3.py`）。金型 `axiom_min.py` は触らない。

リポジトリ: https://github.com/kishimoto-void/Capsule
ライセンス: PolyForm Noncommercial 1.0.0（研究・個人・非営利の再現と改変は可。商用は不可）

---

## いまの定義

```
αβ     封印された基準。Hash-A。観察から書かない
γ      本筋の住所（min3: time / project / topic）
Δ      住所上の更新。閉じた語のみ
IS     正の確定だけ。最大3行。不知は書かない。語は上書き。状態はピン
η      非保存の距離。次の bind を変えうる
Gate   今は Δ 書き込み政策のみ。生成文は見ていない
Render 見える世界
LLM    次トークン予測のまま。アルゴリズムは変えない
```

α は法律ではない。Gate は生成文を α と照合しない。

閉じた Δ 語: 課題 / 改善点 / 結論 / 立場 / 状態
未知語は `adopt_word` するまで書けない。

---

## 動かす

```bash
python3 -m unittest test_axiom_min3.py
python3 phase3_gamma_history.py
```

| ファイル | 役割 |
|----------|------|
| `axiom_min.py` | 金型。触らない |
| `axiom_min2.py` | 7軸γの保存版 |
| `axiom_min3.py` | 作業線。γ = time + project + topic |
| `test_axiom_min3.py` | 単体 51/51 |
| `phase3_gamma_history.py` | 同一 Δ 山の B / M2 / M3 文字数比較 |

---

## 測ったこと（狭い）

Phase 2: 履歴なし・独立5問・採点非提示・3モデル。

| 条件 | I合計 | F合計 | 核合計 | メタ合計 |
|------|-------|-------|--------|----------|
| Baseline | 4 | 8 | 2 | 0 |
| min2 | 0 | 0 | 0 | 0 |
| min3 | 0 | 0 | 0 | 0 |

N=45。記述統計。有意とは言わない。

いま言える上限:

> 閉じた短い外部状態を渡すと、本5問・3モデル・履歴なしでは、長文より未提示具体と核の変更が少なかった。

Phase 3（機械のみ）: 同一15件の Δ 山を全載せすると Baseline は Capsule Render より入力が約7割厚い。差の主因は γ 軸数ではなく、山の全載せ・未確定メモを渡さないこと・IS_MAX=3。topic まで固定すると min2 と min3 のパケット長は一致する。3モデル応答は未測。

詳細: `AXIOM_Phase2_Report.md` / `AXIOM_Phase3_Gamma_History.md` / `AXIOM_Capsule_Paper_Draft.md` / `AXIOM_IS_Pin_Note.md`

---

## 証明していないこと

- モデル非依存の一般
- 履歴ありの F（パケットは用意した。応答は未取得）
- min3 が min2 より強いこと
- ハルシネーション全般
- α が法律として強制されること
- カーネル配置

---

## 古い層

`roleplay_engine.py` / `axiom_memory_capsule.py` / `AXIOM_Capsule_Runtime_Paper.md` は先行ランタイムの記録である。本文の対象は着脱アタッチメントである。層は足さない。
