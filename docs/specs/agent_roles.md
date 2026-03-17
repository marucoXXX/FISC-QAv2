# FISC-QAv2 マルチエージェント構成 — 各エージェントの役割と存在理由

## Context
現状のマルチエージェント構成（Agent 0〜4）を棚卸しし、各エージェントの存在理由・役割・責務を明確化する。これをもとに構成の妥当性を議論するための資料。

---

## パイプライン全体フロー

```
質問票(Excel) → [Orchestrator] → 出力Excel + レビューノート
                    │
                    ├─ 1. read_questionnaire()
                    ├─ 2. [Indexer]  KB全ファイルのインデックス生成
                    ├─ 3. [Router]   質問→KBファイルのマッピング（1回目: 過去回答判定用）
                    ├─ 4. 過去回答の再利用判定
                    ├─ 5. [Router]   新規質問のみ再ルーティング → ReaderAssignment生成
                    ├─ 6. [Reader×N] 並列でKB読み取り＋回答生成（LLM）
                    ├─ 7. [Reviewer] 全回答の品質レビュー
                    └─ 8. write_results()
```

---

## Agent 0: Orchestrator (`src/orchestrator.py`)

### 存在理由
パイプライン全体の制御と状態管理を一箇所に集約するため。各エージェントは独立した単機能モジュールであり、それらの**実行順序・データ受け渡し・並列制御・エラーハンドリング**を担う司令塔が必要。

### 責務
| 責務 | 詳細 |
|------|------|
| **パイプライン制御** | 5段階の処理を順序通り実行（Index → Route → Read → Review → Output） |
| **過去回答の再利用判定** | `kb/past_answers/` から過去回答を読み込み、関連KBファイルが未更新なら過去回答を採用（LLM呼び出しをスキップ） |
| **Reader並列実行** | `ThreadPoolExecutor` で複数Readerを同時実行。ファンアウト/ファンイン構造 |
| **リトライ制御** | Reader失敗時に指数バックオフで最大3回リトライ |
| **結果集約** | 全Readerの回答を `dict[int, Answer]` にマージ。失敗分は「未回答」+LOW信頼度で埋める |
| **Excel入出力** | 質問票の読み込みと結果Excelの書き出し（`excel_io` モジュールに委譲） |

### LLM呼び出し
**なし** — 純粋に制御ロジックのみ

### 入出力
- **入力**: 質問票Excelパス, KBディレクトリ, Config
- **出力**: 出力Excelファイルパス

---

## Agent 1: Indexer (`src/indexer.py`)

### 存在理由
KBの全ファイルを**事前に軽量スキャン**し、Router が質問をルーティングするための情報（ファイル名・カテゴリ・要約・推定トークン数）を提供するため。また、ファイルの**変更検知**により過去回答の再利用可否を判断する基盤を提供する。

### 責務
| 責務 | 詳細 |
|------|------|
| **ファイル走査** | `kb_dir` 配下を再帰走査し、全ファイルを列挙 |
| **要約抽出** | PDF（先頭2ページ）、DOCX（見出し優先）、XLSX（全行）、テキスト（先頭50行）から500文字の要約を生成 |
| **トークン数推定** | ヒューリスティック（日本語2文字/token、英語4文字/token）で全文のトークン数を推定 |
| **変更検知** | ファイルのmtime(ISO8601)を前回インデックスと比較し、`updated` フラグを設定 |
| **LLM要約（オプション）** | `use_llm_summary=True` の場合、LLMで100-200トークンの構造化要約を生成 |
| **インデックスキャッシュ** | JSON形式でインデックスを保存/読み込み（`.fisc_index_cache.json`） |

### LLM呼び出し
- **条件付き**（`use_llm_summary=True` かつ API key あり）
- 用途: 各ファイルの要約を FISC関連性を含めて構造化

### 入出力
- **入力**: KBディレクトリ, 前回インデックス(optional)
- **出力**: `list[IndexEntry]`（file_name, path, category, summary, estimated_tokens, last_modified, updated）

---

## Agent 2: Router (`src/router.py`)

### 存在理由
質問ごとに**どのKBファイルを参照すべきか**を決定し、Readerへの作業割り当てを最適化するため。全質問×全ファイルの総当たりではトークンコストが爆発するため、適切なファイル選定とトークン予算に基づく**ビンパッキング**が必要。

### 責務
| 責務 | 詳細 |
|------|------|
| **LLM動的ルーティング** | インデックス情報と質問リストをLLMに渡し、各質問に1〜3ファイルを割り当て |
| **静的フォールバック** | LLM失敗時、`_KEYWORD_MAP`（12カテゴリ）+ `_CATEGORY_HINTS` でキーワードマッチング |
| **ビンパッキング** | 質問+ファイルを `token_budget_per_reader`（デフォルト80,000）に収まるようReaderに分配 |
| **Reader割り当て生成** | `ReaderAssignment`（reader_id=A/B/C..., questions, files, estimated_tokens）を生成 |

### LLM呼び出し
- **条件付き**（API key あり）
- 用途: 質問→KBファイルの動的マッピング
- max_tokens: 2,048
- フォールバック: 空応答・切断・パースエラー時は静的ルーティングに切り替え

### 入出力
- **入力**: `list[Question]`, `list[IndexEntry]`, token_budget
- **出力**: `RoutingResult`（`list[ReaderAssignment]`）

---

## Agent 3: Reader (`src/reader.py`)

### 存在理由
実際にKBファイルの**全文を読み込み**、LLMを使って質問に対する回答を生成する**中核エージェント**。Routerが割り当てたファイルセットのみを読むことで、トークン消費を制御しつつ、必要な文脈を確保する。

### 責務
| 責務 | 詳細 |
|------|------|
| **KBファイル読み取り** | PDF（PyMuPDF/フォールバック）、DOCX、XLSX、テキストの全文テキスト抽出 |
| **回答生成プロンプト構築** | KB全文 + 質問リストをプロンプトに組み立て |
| **LLM API呼び出し** | `litellm.completion()` で回答JSONを生成（max_tokens: 16,384） |
| **応答パース** | 3段階フォールバック（直接parse → コードブロック抽出 → 括弧深度マッチング） |
| **切断回復** | `finish_reason="length"` 時に閉じ括弧を補完して部分回答を救済 |
| **欠損補完** | LLM応答に含まれなかった質問を「回答不可候補」+LOW信頼度で埋める |
| **OpenAI対応** | OpenAIモデル検出 → `response_format: json_object` を付与 |

### LLM呼び出し
- **必須**（このエージェントの存在意義そのもの）
- システムプロンプト: FISC安全対策基準の専門家として、KBのみに基づき回答
- 出力: JSON配列（question_no, answer, status, source_references, confidence, key_excerpt）
- max_tokens: 16,384

### 入出力
- **入力**: reader_id, `list[Question]`, file paths, kb_base_dir, api_key, model
- **出力**: `list[Answer]`（question_no, answer, status, source_references, confidence, key_excerpt, flag）

---

## Agent 4: Reviewer (`src/reviewer.py`)

### 存在理由
Readerが個別に生成した回答を**横断的に検証**するため。各Readerは自分の担当ファイルしか見ていないため、回答間の**矛盾検出**や**信頼度の一貫性確保**が必要。また、LLMの判断ミスを補正する**ルールベースの安全ネット**を提供する。

### 責務
| 責務 | 詳細 |
|------|------|
| **LLMレビュー** | 全回答サマリーをLLMに渡し、矛盾検出・根拠妥当性チェック・最終信頼度判定を実施 |
| **信頼度/ステータス上書き** | LLMの `final_judgments` に基づき、confidence と status をオーバーライド |
| **レビューノート生成** | `ReviewNote`（issue_type, severity, description, suggestion）を生成 |
| **ルールベースレビュー** | LLM結果の上に常に適用される決定論的ルール: |
|  | - LOW信頼度 → status=「回答不可」に強制 |
|  | - 回答テキスト空 + HIGH/MEDIUM信頼度 → LOW に降格 + 「回答不可」 |
| **フォールバック** | LLMレビュー失敗時（空応答/切断/パースエラー）→ ルールベースのみで処理 |

### LLM呼び出し
- **条件付き**（API key あり）
- 用途: 全回答の横断レビュー（矛盾、根拠不足、信頼度補正）
- max_tokens: 8,192
- フォールバック: ルールベースレビューのみ

### 入出力
- **入力**: `list[Question]`, `dict[int, Answer]`, api_key, model
- **出力**: (`dict[int, Answer]`（上書き済み）, `list[ReviewNote]`)

---

## エージェント間の依存関係

```
Indexer ─────→ Router ─────→ Reader(s) ─────→ Reviewer
  │              │              │                 │
  │              │              │                 │
IndexEntry[]  RoutingResult  Answer[]     Answer[] + ReviewNote[]
  │              │              │                 │
  └──────────────┴──────────────┴─────────────────┘
                         ↑
                   Orchestrator が制御
```

| 依存関係 | 説明 |
|----------|------|
| Router → Indexer | ルーティングにはインデックス情報（ファイル名・要約・トークン数）が必要 |
| Reader → Router | Readerの担当ファイル・質問はRouterが決定 |
| Reviewer → Reader | レビュー対象はReaderが生成した回答 |
| Orchestrator → 全エージェント | 実行順序・データ受け渡し・並列化・リトライを制御 |

---

## 各エージェントのLLM依存度まとめ

| Agent | LLM必須? | LLM用途 | LLMなしの動作 |
|-------|----------|---------|---------------|
| Orchestrator | 不要 | — | 完全動作 |
| Indexer | オプション | ファイル要約強化 | ローカル抽出のみ（500文字） |
| Router | オプション | 動的ルーティング | 静的キーワードマッチング |
| Reader | **必須** | 回答生成 | **動作不可** |
| Reviewer | オプション | 横断レビュー | ルールベースのみ（2ルール） |

---

## 議論ポイント（検討用）

この整理をもとに、以下のような観点で構成を議論できます:

1. **Router の必要性**: 静的ルーティングで十分なら、LLMルーティングのコスト/遅延は削減可能か？
2. **Reviewer のLLMレビュー**: ルールベースだけで十分か、LLMレビューの付加価値はどの程度か？
3. **Indexer のLLM要約**: 使われているケースはあるか？ローカル抽出で十分か？
4. **Reader の分割粒度**: 現在の80,000トークン/Readerは適切か？
5. **Orchestrator の過去回答ロジック**: 過去回答の再利用判定はOrchestratorにあるべきか、別エージェントに分離すべきか？
