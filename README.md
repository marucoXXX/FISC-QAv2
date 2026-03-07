# FISC-QAv2 — FISCアンケート自動回答システム

金融情報システムセンター（FISC）の金融機関向けアンケートに対し、社内ドキュメントを根拠としてAIが回答案を自動生成するシステムです。

---

## システム概要

| 項目 | 内容 |
|------|------|
| 入力 | FISCアンケート回答票（Excel） |
| 知識ベース | 社内ポリシー・過去回答・設計書（数百ファイル対応） |
| AI | Claude API（Anthropic） |
| 出力 | 回答済みExcel（回答・根拠・信頼度スコア・🚩フラグ） |

---

## アーキテクチャ

**Sequential + Concurrent マルチエージェント構成**（Microsoft Azure Architecture Center パターン準拠）

```
questionnaire.xlsx
      ↓
  [Agent 0] Orchestrator      ← 全体フロー制御
      ↓
  [Agent 1] Indexer           ← KB先頭ページのみ読み・軽量インデックス生成
      ↓
  [Agent 2] Router ⚡SWAPPABLE ← トークン予算でReader数を動的決定
      ↓ (並列dispatch)
  [Agent 3] Parallel Readers  ← 割当ファイル全文読み・回答生成（Concurrent）
      ↓ (構造化サマリーのみFan-in)
  [Agent 4] Reviewer          ← 矛盾チェック・信頼度判定・🚩フラグ付与
      ↓
  Review UI → 人間承認 → completed_answers.xlsx
```

詳細は [`docs/diagrams/multiagent_architecture_v3.html`](docs/diagrams/multiagent_architecture_v3.html) を参照。

---

## ドキュメント構成

```
docs/
├── diagrams/
│   ├── multiagent_architecture_v3.html   # マルチエージェント構成図（スタンドアロン）
│   └── dataflow_diagram_v3.html          # データフロー図（ユーザー/システム スイムレーン）
├── specs/
│   └── architecture_spec.md              # AI解釈可能アーキテクチャ仕様（YAML形式）
└── roadmap/
    ├── mvp_roadmap.md                    # MVPロードマップ（テキスト版）
    └── mvp_roadmap_visual.html           # MVPロードマップ（ビジュアル版）
```

> **HTMLファイルはすべてスタンドアロン**（外部依存なし）。`file://` で直接開けます。

---

## 技術スタック

| レイヤー | 技術 |
|----------|------|
| バックエンド | Python 3.11+ / FastAPI |
| AIモデル | claude-sonnet-4-5（Reader/Reviewer）/ claude-haiku（Router） |
| ドキュメント処理 | PyMuPDF / python-docx / openpyxl |
| フロントエンド | React |
| 出力 | Excel（openpyxl） |

---

## 開発フェーズ

| フェーズ | 内容 | 状態 |
|----------|------|------|
| Phase 1 | テストデータ準備 | 🔲 Next |
| Phase 2 | バックエンド実装 | 🔲 |
| Phase 3 | フロントエンド実装 | 🔲 |
| Phase 4 | 結合・テスト | 🔲 |
| Phase 5 | 社内デモ準備 | 🔲 |

---

## セットアップ（実装開始後に追記予定）

```bash
# 環境変数
cp .env.example .env
# ANTHROPIC_API_KEY=your_key_here を設定

# バックエンド
pip install -r requirements.txt
uvicorn main:app --reload

# フロントエンド
cd frontend && npm install && npm run dev
```

---

## 参照

- [Microsoft Azure Architecture Center — AI Agent Orchestration Patterns](https://learn.microsoft.com/en-us/azure/architecture/ai-ml/guide/ai-agent-design-patterns)
- [Anthropic Claude API](https://docs.anthropic.com/)
- FISC「金融機関等コンピュータシステムの安全対策基準・解説書」第13版
