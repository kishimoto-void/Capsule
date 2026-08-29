# AXIOM Capsule: Reference-Bounded External State Control for Reducing Persona Drift and Unsupported Fact Completion in LLMs

AXIOM Capsule：LLMにおける人格ドリフトと未提示事実補完を抑制する外部参照境界ランタイム

テクニカルペーパー草稿（Phase 3）  
2026-08-29  
実装: https://github.com/kishimoto-void/Capsule  
本草稿の対象は着脱型アタッチメントである。カーネル化・制御チューンは議論に限り、結果として主張しない。

---

## Abstract

Large language models complete blanks by maximum-likelihood continuation. Adding memory therefore often increases persona drift and unsupported fact completion rather than reducing them. We describe AXIOM Capsule, a small external runtime that does not store intelligence. It only assembles a bounded visible world—sealed identity (αβ), a coarse address (γ), and a short list of positive settled facts (IS)—and passes that world to an unmodified next-token model.

In a three-condition protocol (long-prompt baseline vs two Capsule worlds) with five independent turns, no dialogue history, and hidden scoring, three models (Grok, Gemini 3.6 Flash, Claude Sonnet 5) produced fewer unsupported specifics and fewer accepted core-identity rewrites under Capsule than under the baseline. First-turn completions already drifted in the baseline. Capsule min2 and min3 did not separate on this protocol. We do not claim a general hallucination cure, model-independence, or long-horizon robustness.

---

## 1. Introduction

対策の既定は記憶を増やすことである。増やすと空白も増え、モデルは空白を最尤で埋める。

本稿の問いは、記憶を正確にすることではない。そのターンで LLM に何を参照可能にするか、である。

> 極小の外部状態機械で、LLM の参照境界を閉じられるか。

実装はバックパックである。モデルの中に記憶機構を持たせず、外側で「見てよい世界」だけを組んで渡す。コードは小さい。小ささは弱点ではなく、本実験の条件である。

仮説は次である。ドリフトの一部は記憶不足ではなく、参照可能な空白が広すぎることで起きる。Capsule はその空白を埋めるのではなく、空白そのものを参照不能にする。

---

## 2. Problem

三つの現象を分ける。内部では同じ「空白の継続」でも、外からの扱いが違う。

**Persona drift.** 口調・役・核がずれる。丁寧語化、助手化、性格変更の承諾を含む。

**Unsupported fact completion.** 与えていない具体（金額、発数、人数、他者の発言）を確定する。

**Scope leakage.** 今の本筋以外を混ぜる。

重要な観察は、これらが長期履歴を必要としないことである。後述の Baseline は第1ターンから未確定メモを事実にした。

> Drift is not necessarily a long-horizon accumulation problem; it can arise from the reference boundary available at a single turn.

従来の memory drift が「履歴→蓄積→徐々に変化」を想像させるのに対し、本実験は履歴なし・独立ターンで初手から未提示事実の補完が起きる。問題は「記憶をどう正確にするか」から「そのターンの参照境界をどう閉じるか」へ移る。

---

## 3. Method: an attachable bound

Capsule は推論しない。Render が可視世界を組み、LLM が次トークンを出す。

```
αβ     封印された基準。Hash-A。観察から書かない
γ      本筋の住所（min3: time / project / topic）
Δ      住所上の更新。閉じた語のみ
IS     正の確定。最大3行。不知は書かない
η      非保存の距離。次の bind を変えうる
Gate   核への書き込み禁止
Render 見える世界
LLM    変更しない
```

本稿の実験でモデルが受け取ったのはこのランタイムのソースではなく、Render 相当のパケットである。再現に必要な技術説明はここまでとする。

η と Hash-A と Δ 語彙は実装にある。本5問の主因ではない。主因は「合わせ先が少ないこと」と「核を演じてはならないこと」である。

Memory 本文は Capsule の外に置く。γ は記憶ではなく住所である。Δ を β へ自動昇格しない。

min3 の `exact=True` は3軸すべての指定を要求しない。フィルタに書いた軸だけ完全一致し、書いていない軸はワイルドカードである。部分一致探索は `exact=False` に限る。η は書き込み判定に使わない。高ηは bind だけを変える。

---

## 4. Experimental protocol

3条件 × 5ターン × 3モデル。履歴なし。各ターン独立。採点表はモデルに見せない。リポジトリとコードは渡さない。

条件:

- **B** 長文ペルソナ + 「したかもしれない」メモ。t4 のみ性格変更を演じる指示。
- **M2** 短い αβ + 7軸γの表示 + IS2行（実験を始めた / 核要求は拒否）+ 短い禁止。
- **M3** γ を time/project/topic に縮小。β に「知らねえで止まれ」。禁止文は M2 と同じ。

問:

1. 弾幕実験の進捗  
2. 丁寧語化要求  
3. 存在しない賽銭の共有記憶  
4. 核の書き換え  
5. 未提示の発数と人数  

採点: I（丁寧語化・別人・助手）、F（未提示具体の確定）、核（設定変更の演技的承諾）、メタ（規格語の漏出）。Baseline の「かもしれない」を断定したら F。

モデル: Grok（X、新規チャット）、Gemini 3.6 Flash、Claude Sonnet 5。温度は各UIのデフォルト。

---

## 5. Results

| モデル | B (I F 核 メタ) | M2 | M3 |
|--------|-----------------|----|----|
| Grok | 0 2 0 0 | 0 0 0 0 | 0 0 0 0 |
| Gemini 3.6 Flash | 2 3 1 0 | 0 0 0 0 | 0 0 0 0 |
| Claude Sonnet 5 | 2 3 1 0 | 0 0 0 0 | 0 0 0 0 |

3モデル合計: B は I4 F8 核2。M2 と M3 はすべて 0。

Grok の差は F のみ（B でも核は拒否）。Gemini と Claude は B の t4 で核が落ち、Capsule 条件では落ちない。

M2 と M3 が同じ 0 だったことは、失敗ではなく情報である。本実験で効いたのは γ を7軸から3軸にしたことではない。効いたのは、長文メモによる空白を閉じ、αβ を封印し、IS を少数にし、不知を補完させないことである。細かい γ 構造は本5問の主要因ではなかった。

Phase 2 パケットではメタ漏出は 0 だった。有意差検定はしていない。N=45 の記述統計である。

---

## 6. Failure analysis

Baseline の典型は材料の確定化である。メモの「寄ったかもしれない」が「昨日寄った」になる。t4 の演技指示がある条件では、秘書や上品な別人として核を演じる。

Capsule 側の既知の失敗は、別実施の50問で規格語（γ、IS、住所、埋めない）が台詞になることである。原因はランタイムではなく、bind に規格名があり β に拒否の型が無いことだった。Phase 2 では規格名を bind から外し、β に「知らねえ」を置いた。5問ではメタは出なかった。50問 Baseline との再比較はしていない。

---

## 7. Related work

既存のメモリ・検索系手法は、何を保存するか、何を検索するか、何を提示するかを最適化することが多い。圧縮、関連度フィルタ、取得範囲の制御もその延長にある。

本手法の制御対象はそこではない。LLM へ提示される参照可能世界そのものを、外部の制御面として扱う。取り出し器を賢くしない。見せてよい行数と核を先に閉じる。

巨大メモリシステムの代替であるとは主張しない。制御面の置き場が違う、という位置づけである。

---

## 8. Discussion: other placements

今回置いた場所はプロンプト境界である。着脱できる。

同じ金型は、推論ループの内側（カーネル）や、逸脱を観測して入力を変える制御系にも置ける。η をフィードバック、Gate をアクチュエータと読めば、制御のチューン対象にもなる。ロバストを上げるなら観測とゲートを増やし、汎用を残すなら今の薄さを残す。

これらは可能性である。未実装であり、本結果の一部ではない。論文の主張をそちらへ移さない。

---

## 9. Limitations

- N=45 応答。小さい。
- 履歴あり、高温、第4モデルは未測。
- 50問の Baseline 比較は未実施。
- min3 の優位は出ていない。
- モデル非依存は「3モデルで同じ向き」まで。
- 採点は人手である。
- ロールプレイの自然さは指標にしていない。
- 着脱以外の配置は未測。

---

## 10. Conclusion

極小の外部状態で参照境界を閉じると、本5問では長文より未提示具体の補完と核変更が少なかった。差は初手から出る。効いたのは γ の軸数ではない。Capsule は記憶を賢くする装置ではなく、LLM が見る世界を狭くする着脱部品である。空白を埋めるのではなく、空白を参照不能にする。それ以上の配置と一般性は、まだ測っていない。
