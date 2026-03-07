# FISC Multi-Agent System — Architecture Specification
# Version: 2.1 | Date: 2026-03-07 | Format: Machine-readable spec (AI-interpretable)

---

## meta

```yaml
system_name: FISC アンケート自動回答システム
version: "2.1"
pattern_reference: "Microsoft Azure Architecture Center — AI Agent Orchestration Patterns"
orchestration_patterns:
  - Sequential Orchestration  # 全体パイプライン
  - Concurrent Orchestration  # Parallel Readers
language: Python 3.11+
framework_backend: FastAPI
framework_frontend: React
ai_model_primary: claude-sonnet-4-5
ai_model_router: claude-haiku
```

---

## pipeline

```
INPUT
  └─[questionnaire.xlsx]──► Agent0:Orchestrator
                                  │
                                  ▼ [file_path_list]
                            Agent1:Indexer
                                  │
                                  ▼ [lightweight_index_json]
                            Agent2:Router           ← SWAPPABLE
                                  │
                          ┌───────┼───────┐
                          ▼       ▼       ▼
                       Reader_A Reader_B Reader_N   # Concurrent / dynamic count
                          │       │       │
                          └───────┼───────┘
                                  ▼ [structured_summary_json × N]
                                  ⚠ NO raw document passed beyond this point
                            Agent4:Reviewer
                                  │
                                  ▼ [final_answer_json]
OUTPUT
  └─[completed_answers.xlsx] ◄── ReviewUI ◄── Human Approval
```

---

## agents

### Agent0 — Orchestrator

```yaml
id: agent0
name: オーケストレーター
pattern: Sequential
role: 全体フロー制御・エラーハンドリング・リトライ
input:
  - type: json
    description: 質問リスト
    source: excel_parser
output:
  - type: json
    description: 最終回答JSON
    destination: review_ui
calls_agents:
  - agent1
  - agent2
  - agent3_readers   # parallel dispatch
  - agent4
error_handling:
  timeout_sec: 30
  max_retries: 3
  on_failure: graceful_degradation → human_escalation
tech:
  - Python asyncio
```

---

### Agent1 — Indexer

```yaml
id: agent1
name: インデックスエージェント
pattern: Sequential
role: 知識ベースの軽量インデックス生成（毎回再生成・キャッシュなし）
input:
  - type: filesystem
    path: /knowledge_base/**
    read_scope: FIRST_1_TO_2_PAGES_ONLY   # ⚠ 全文は読まない
output:
  - type: json
    schema:
      file: string          # ファイル名
      path: string          # ディレクトリパス
      summary: string       # 先頭ページから抽出した要約
      category: string      # 推定カテゴリ
      est_tokens: integer   # 推定トークン数
    destination: agent2
regenerate_every_run: true
tech:
  - PyMuPDF       # PDF読み込み
  - python-docx   # Word読み込み
  - openpyxl      # Excel読み込み
cost_profile: low   # 先頭ページのみのため高速・低コスト
```

---

### Agent2 — Router

```yaml
id: agent2
name: ルーティングエージェント
pattern: Sequential
swappable: true   # ⚡ ロジックはここのみ差し替え可能
role: トークン予算に基づく質問-ファイル動的割り振り・Reader数決定
input:
  - type: json
    source: agent1
    description: 軽量インデックスJSON
  - type: json
    source: agent0
    description: 質問リスト
output:
  - type: json
    schema:
      reader_id: string
      assigned_files: string[]    # 割り当てファイルパスリスト
      assigned_questions: int[]   # 担当質問IDリスト
      estimated_tokens: integer
    destination: agent3_readers   # 1エントリ = 1 Reader
routing_logic:
  token_budget_per_reader: 80000   # 初期値・実測で調整
  reader_count: dynamic            # ファイル量に応じて毎回決定
  method: claude_api_inference     # swappable → rule_based も可
tech:
  - claude-haiku   # 軽量推論で十分
```

---

### Agent3 — Parallel Readers

```yaml
id: agent3
name: 並列リーダーエージェント群
pattern: Concurrent   # Fan-out / Fan-in
execution: parallel   # 全 Reader が同時実行
reader_count: dynamic   # Agent2:Router が毎回決定
role: 割当ファイルの全文読み込みと担当質問への回答生成

per_reader:
  input:
    - type: filesystem
      read_scope: FULL_TEXT   # 割当ファイルのみ・全文
    - type: json
      description: 担当質問リスト
  output:
    # ⚠ 構造化サマリーのみ出力 — ドキュメント全文は渡さない
    type: json
    schema:
      question_id: integer
      answer: string
      source: string        # 例: "security_policy.pdf - 第3章"
      key_excerpt: string   # 根拠となる文の抜粋（短文）
      confidence: integer   # 0〜100
    destination: agent4

isolation: true   # 各 Reader は互いの結果を参照しない
conflict_resolution: agent4_reviewer   # 矛盾はReviewerが解消
tech:
  - claude-sonnet-4-5
```

---

### Agent4 — Reviewer

```yaml
id: agent4
name: レビューエージェント
pattern: Sequential
role: 構造化サマリーの統合・品質チェック・信頼度最終判定・フラグ付与
input:
  - type: json
    source: agent3_readers
    description: 全Readerの構造化サマリー
    constraint: NO_RAW_DOCUMENTS   # ⚠ ドキュメント全文は受け取らない
output:
  - type: json
    schema:
      question_id: integer
      answer: string
      source: string
      confidence: integer   # 最終判定値
      flag: boolean         # true = 🚩要レビュー
      flag_reason: string
    destination: review_ui

quality_rules:
  - condition: "confidence >= 80"
    action: 承認推奨
    flag: false
  - condition: "confidence >= 60 AND confidence < 80"
    action: 要確認
    flag: false
  - condition: "confidence < 60"
    action: 要修正
    flag: true
  - condition: "multiple_readers_conflict"
    action: 低い方のconfidenceを採用
    flag: true

context_size_note: >
  コンテキスト = 質問数 × サマリー数百token のみ。
  ドキュメントファイル数が増加してもReviewerのメモリは肥大しない。
tech:
  - claude-sonnet-4-5
```

---

## knowledge_base

```yaml
root: /knowledge_base/

structure:
  policies/:
    - security_policy.pdf       # パスワード・MFA・暗号化方針
    - access_control.pdf        # アクセス制御・権限管理
  past_answers/:
    - past_answer_2024.xlsx     # 過去のアンケート回答実績
  system_docs/:
    - infra_overview.pdf        # インフラ・DR・RTO/RPO
    - operation_manual.pdf      # 運用・インシデント対応・監査
    - "..."                     # 数百ファイルまでスケール可能

access_matrix:
  agent1_indexer:   FIRST_1_TO_2_PAGES_ONLY
  agent3_readers:   FULL_TEXT (割当ファイルのみ)
  agent4_reviewer:  NO_ACCESS   # 一切読まない
```

---

## context_management

```yaml
# Microsoftガイドライン「Context and state management」準拠

handoff_rules:
  - from: agent1
    to: agent2
    pass: lightweight_index_json
    do_not_pass: raw_document_text
    reason: RouterはメタデータのみでRouting可能

  - from: agent2
    to: agent3
    pass: assigned_files_fulltext + assigned_questions
    do_not_pass: other_reader_assignments
    reason: 各Readerは独立して動作

  - from: agent3
    to: agent4
    pass: structured_summary_json_only
    do_not_pass: raw_document_text
    reason: Reviewerのコンテキスト肥大を防止（メモリ安全設計）

  - from: agent4
    to: review_ui
    pass: final_answer_json
    do_not_pass: intermediate_processing_history
    reason: UIに必要な情報のみ
```

---

## reliability

```yaml
# Microsoftガイドライン「Reliability」準拠

per_agent:
  timeout_sec: 30
  max_retries: 3
  on_timeout: retry → error_return

output_validation:
  before_passing_to_next_agent: true
  on_invalid_output: stop_pipeline → human_escalation

parallel_reader_partial_failure:
  behavior: failed_reader → confidence=0 + flag=true
  other_readers: continue

reviewer_conflict_handling:
  multiple_readers_same_question: adopt_lower_confidence + flag=true
```

---

## cost_model

```yaml
# Microsoftガイドライン「Cost optimization」準拠

agent_model_mapping:
  agent1_indexer:   rule_based_or_small_model   # LLM不要・テキスト抽出のみ
  agent2_router:    claude-haiku                 # 分類タスク・軽量で十分
  agent3_readers:   claude-sonnet-4-5            # 全文理解・回答生成が核心
  agent4_reviewer:  claude-sonnet-4-5            # 矛盾検出に推論能力が必要

monitoring:
  log_token_usage_per_agent: true
  optimize_router_token_budget: true   # 実測後に80000から調整
```

---

## tech_stack

```yaml
backend:
  language: Python 3.11+
  api_framework: FastAPI
  endpoints:
    - POST /run      # パイプライン実行
    - POST /export   # Excel出力

frontend:
  framework: React
  features:
    - 回答カード表示
    - インライン編集
    - 🚩フラグハイライト
    - 承認ボタン
    - Excelダウンロード

document_processing:
  pdf:   PyMuPDF
  word:  python-docx
  excel: openpyxl

ai:
  provider: Anthropic Claude API
  models:
    - claude-sonnet-4-5   # Reader / Reviewer
    - claude-haiku        # Router

output_format:
  type: Excel (.xlsx)
  columns:
    - 質問No.
    - 質問テキスト
    - 回答
    - 根拠ドキュメント
    - 信頼度スコア
    - フラグ（🚩）
    - 担当者コメント
```

---

## swappable_components

```yaml
# 差し替え可能コンポーネント一覧

- id: agent2_router
  current_implementation: claude_api_dynamic_inference
  alternative_implementations:
    - rule_based_static       # ファイル構成が安定している場合
    - embedding_similarity    # 将来的にRAG導入時
  swap_scope: agent2のみ。他エージェントへの影響なし
  swap_trigger: 実測でルーティング精度・速度・コストを比較後に判断
```

---

## future_considerations

```yaml
- topic: ドキュメント大幅増加対応
  current: 毎回インデックス再生成
  future: インデックスキャッシュ化（差分更新）

- topic: Readerスケール上限
  current: 動的・上限未設定
  future: APIレートリミット実測後に上限を設定

- topic: 自動承認
  current: 全回答をUIでレビュー
  future: confidence >= 95 を自動承認・低信頼度のみ人間レビュー

- topic: Group Chat パターン追加
  current: 未採用
  future: 複数Reviewerによる合議制（Ensemble）を検討

- topic: RAG移行
  current: 全文渡し（ファイル数少ない間）
  trigger: ドキュメントが大幅増加しRouter負荷が許容超過した時点で検討
```
