# AXIOM Capsule Runtime — Prototype

日付: 2026-08-23  
位置づけ: **動く最小核**。製品ではない。Capsule に知能は入れない。

## 何をプロトタイプとするか

```
Capsule   = 状態の正本と同一性境界
Runtime   = Control Prompt の組み立てと生成器呼び出し
LLM       = 拘束された生成
Observer  = 応答の観測（核は書き換えない）
Gate      = 書き戻し制限（β禁止 / γは人間のみ / εのみ可）
```

この4+1分割で凍結する。

## 入っているもの

| 部品 | ファイル | 状態 |
|------|----------|------|
| Double Capsule Memory v3.2 | `attachments/axiom_memory_capsule.py` | 単体デモ 8/8 PASS |
| RoleplayEngine + Control Prompt | `artifacts/roleplay_engine.py` | stub / manual 接続 |
| Observer + WritebackGate | 同上 | 校正セット済み |
| 技術ノート | `artifacts/AXIOM_Capsule_Runtime_Paper.md` | 実装と実測のみ記載 |

実験核: 霧雨魔理沙（Hash-A 固定）。東方二次創作・個人実験用途。

## 入っていないもの（意図的）

- LLM API 接続
- 賢い Capsule
- 自動 γ 定着
- 高度な adherence（埋め込み判定など）
- 複数相手の本格運用
- UI

## 動かした事実

- Capsule 単体: A–H すべて PASS
- stub `full_turn` 5手: Hash-A 不変、core_intact 維持
- manual LLM 7手: 口調維持、Ζ mild→tense、γ は空（ゲートどおり）
- Observer 校正: 丁寧語=epsilon_only、別人化=forbidden、核口調=promote_request

## 実行

```
python3 roleplay_engine.py          # stub CLI
python3 roleplay_engine.py manual   # 制御プロンプトを外部LLMへ
python3 roleplay_engine.py demo     # 固定シナリオ + Observer校正
```

`/state` `/prompt` `/observe` `/approve` `/reject` `/sign +1|0|-1` `/quit`

## 凍結ルール

1. Capsule はこれ以上賢くしない。
2. Observer の結果で β / Hash-A を更新しない。
3. γ 定着は人間承認のみ。
4. 次に足すなら Runtime / Observer / API generator であり、核ではない。

## 次にやるなら（プロトタイプの外）

- 壊し実験を増やす（過剰共感、上手い別人化）
- 30ターン超の長期軌道
- `Callable[[str], str]` に API generator を差す
