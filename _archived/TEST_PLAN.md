# FISC-QAv2 テストカバレッジ強化計画

現状: 86テスト / 推定カバレッジ ~70%
目標: ~200テスト / カバレッジ ~90%

---

## Phase 1: 未テストモジュール (CRITICAL)

### 1-1. CLI テスト (`tests/test_cli.py` 新規)

`src/__main__.py` の全8関数が完全に未テスト。

| # | テストケース | 対象関数 | 概要 |
|---|------------|---------|------|
| 1 | test_cli_qa_valid_inputs | `cmd_qa` | questionnaire + kb_dir で正常実行 |
| 2 | test_cli_qa_custom_output_dir | `cmd_qa` | --output-dir フラグ |
| 3 | test_cli_qa_missing_questionnaire | `cmd_qa` | 必須引数なしでエラー |
| 4 | test_cli_index_generates_json | `cmd_index` | インデックス JSON 出力 |
| 5 | test_cli_index_with_previous | `cmd_index` | --previous で更新検知 |
| 6 | test_cli_index_llm_summary | `cmd_index` | --use-llm-summary フラグ |
| 7 | test_cli_route_with_questionnaire | `cmd_route` | ルーティングマップ生成 |
| 8 | test_cli_route_with_index_file | `cmd_route` | --index ファイル指定 |
| 9 | test_cli_read_filters_questions | `cmd_read` | --questions フィルタ |
| 10 | test_cli_read_custom_reader_id | `cmd_read` | --reader-id 指定 |
| 11 | test_cli_review_processes_answers | `cmd_review` | 回答 JSON 処理 |
| 12 | test_cli_serve_creates_app | `cmd_serve` | FastAPI 起動確認 |
| 13 | test_cli_token_budget_override | `_add_common_args` | --token-budget 上書き |
| 14 | test_cli_model_override | `_add_common_args` | --model 上書き |
| 15 | test_cli_help_output | `main` | --help 表示 |

### 1-2. Config テスト (`tests/test_config.py` 新規)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_config_defaults | デフォルト値の確認 |
| 2 | test_config_from_env_fisc_kb_dir | FISC_KB_DIR 環境変数 |
| 3 | test_config_from_env_fisc_model | FISC_MODEL 環境変数 |
| 4 | test_config_from_env_output_dir | FISC_OUTPUT_DIR 環境変数 |
| 5 | test_config_from_env_token_budget | FISC_TOKEN_BUDGET 環境変数 |
| 6 | test_config_invalid_token_budget | 非整数の FISC_TOKEN_BUDGET |
| 7 | test_config_default_model_version | デフォルトモデル名の確認 |

---

## Phase 2: 新カテゴリ・ルーティング (HIGH)

### 2-1. 新カテゴリのルーティングテスト (`test_router.py` 追加)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_router_outsourcing_routes_to_regulations | 外部委託管理 → regulations/outsourcing_management.pdf |
| 2 | test_router_system_dev_routes_to_regulations | システム開発 → regulations/system_development_standards.docx |
| 3 | test_router_logging_routes_to_operations | ログ・監視 → operations/vulnerability_assessment_2024.pdf |
| 4 | test_indexer_operations_category | operations/ ファイルのカテゴリが正しいこと |
| 5 | test_indexer_regulations_category | regulations/ ファイルのカテゴリが正しいこと |
| 6 | test_indexer_change_log_xlsx_indexed | operations/change_management_log.xlsx がインデックスされること |
| 7 | test_router_new_categories_all_assigned | 新3カテゴリの全質問がソースに割り当てられること |

### 2-2. Reader の新ファイル形式テスト (`test_reader.py` 追加)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_operations_pdf_readable | operations/ の PDF が読めること |
| 2 | test_operations_docx_readable | operations/ の DOCX が読めること |
| 3 | test_operations_xlsx_readable | operations/ の XLSX が読めること |
| 4 | test_regulations_pdf_readable | regulations/ の PDF が読めること |
| 5 | test_regulations_docx_readable | regulations/ の DOCX が読めること |

---

## Phase 3: Web API テスト (HIGH)

### 3-1. API エンドポイントテスト (`tests/test_web_api.py` 新規)

| # | テストケース | エンドポイント | 概要 |
|---|------------|--------------|------|
| 1 | test_api_config_get | GET /api/config | 現在設定の取得 |
| 2 | test_api_config_update_partial | PATCH /api/config | 一部フィールド更新 |
| 3 | test_api_config_invalid_token_budget | PATCH /api/config | 不正値でエラー |
| 4 | test_api_pipeline_start | POST /api/pipeline/start | パイプライン起動 |
| 5 | test_api_pipeline_start_no_kb | POST /api/pipeline/start | KB未指定でエラー |
| 6 | test_api_pipeline_start_invalid_file | POST /api/pipeline/start | 非 xlsx でエラー |
| 7 | test_api_pipeline_concurrent_start | POST /api/pipeline/start | 二重起動拒否 |
| 8 | test_api_pipeline_status | GET /api/pipeline/{id}/status | ジョブ状態取得 |
| 9 | test_api_pipeline_progress_sse | GET /api/pipeline/{id}/progress | SSE ストリーム |
| 10 | test_api_import_excel_missing_review_sheet | POST /api/runs/import | レビューシートなし |
| 11 | test_api_import_excel_null_cells | POST /api/runs/import | 空セルのハンドリング |
| 12 | test_api_import_json_missing_review_notes | POST /api/runs/import | review_notes キーなし |
| 13 | test_api_export_approved_only | GET /api/runs/{id}/export | 承認済みのみエクスポート |

### 3-2. DB レイヤーテスト (`test_web.py` 追加)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_db_concurrent_review_updates | 同時レビュー更新の整合性 |
| 2 | test_db_transaction_rollback | 例外時のロールバック |
| 3 | test_db_get_answers_empty_run | 回答なしの run |
| 4 | test_db_set_review_nonexistent_answer | 存在しない質問のレビュー |
| 5 | test_db_bulk_set_review_empty_list | 空リストの一括更新 |

### 3-3. Pipeline テスト (`tests/test_pipeline.py` 新規)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_pipeline_job_creation | ジョブ生成と追跡 |
| 2 | test_pipeline_concurrent_jobs_blocked | セマフォによる同時実行防止 |
| 3 | test_pipeline_job_cleanup | 完了後のジョブクリーンアップ |
| 4 | test_pipeline_progress_capture | 進捗メッセージのキャプチャ |
| 5 | test_pipeline_error_propagation | エラー時の状態遷移 |

---

## Phase 4: エラーハンドリング (MEDIUM)

### 4-1. ファイル I/O エラー

| # | テストケース | モジュール | 概要 |
|---|------------|----------|------|
| 1 | test_read_questionnaire_corrupted_xlsx | excel_io | 壊れた Excel |
| 2 | test_read_questionnaire_missing_columns | excel_io | 必須列なし |
| 3 | test_write_results_permission_denied | excel_io | 書き込み権限なし |
| 4 | test_indexer_empty_pdf | indexer | テキストなし PDF |
| 5 | test_indexer_file_encoding_error | indexer | 非 UTF-8 ファイル |
| 6 | test_reader_file_not_found | reader | 参照 KB ファイルなし |
| 7 | test_indexer_pdf_no_fitz_fallback | indexer | PyMuPDF 未インストール時 |

### 4-2. API/LLM エラー

| # | テストケース | モジュール | 概要 |
|---|------------|----------|------|
| 1 | test_reader_api_timeout | reader | タイムアウト |
| 2 | test_reader_api_rate_limit | reader | 429 レートリミット |
| 3 | test_reader_api_auth_error | reader | 401 認証エラー |
| 4 | test_reviewer_api_empty_response | reviewer | 空レスポンス |
| 5 | test_router_llm_malformed_json | router | 不正 JSON レスポンス |

### 4-3. データバリデーション

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_reader_response_missing_question_no | question_no 欠落 |
| 2 | test_reader_response_invalid_confidence | 不正な confidence 値 |
| 3 | test_reviewer_response_invalid_severity | 不正な severity |
| 4 | test_router_empty_index | インデックスが空 |

---

## Phase 5: エッジケース (MEDIUM)

### 5-1. Router エッジケース

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_router_all_same_category | 全質問が同一カテゴリ |
| 2 | test_router_no_matching_files | マッチなし→フォールバック |
| 3 | test_router_single_file_kb | KB にファイル1つだけ |
| 4 | test_router_zero_token_budget | トークン予算 0 |

### 5-2. Reader エッジケース

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_reader_max_tokens_truncated | max_tokens でレスポンス切断 |
| 2 | test_reader_all_unanswerable | 全質問「回答不可」 |
| 3 | test_reader_multi_file_context | 複数ファイルからの複合回答 |

### 5-3. Reviewer エッジケース

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_reviewer_all_high_confidence | 変更不要ケース |
| 2 | test_reviewer_all_low_confidence | 全件「回答不可」 |
| 3 | test_reviewer_contradictory_answers | 矛盾回答の検出 |
| 4 | test_reviewer_past_answer_mix | 過去回答と新規回答の混在 |

### 5-4. Indexer エッジケース

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_indexer_empty_directory | KB ディレクトリが空 |
| 2 | test_indexer_hidden_files_ignored | .DS_Store 等の除外 |
| 3 | test_indexer_duplicate_filenames_across_dirs | 同名ファイルの区別 |

---

## Phase 6: 統合テスト (MEDIUM)

### 6-1. パイプライン統合 (`tests/test_integration.py` 新規)

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_indexer_to_router_to_reader_mock | 3エージェント連携 (mock API) |
| 2 | test_reader_to_reviewer_mock | Reader → Reviewer (mock API) |
| 3 | test_past_answer_reuse_skips_reader | 過去回答再利用で Reader スキップ |
| 4 | test_large_token_splits_readers | 大トークン時の Reader 分割 |
| 5 | test_kb_update_triggers_rerouting | KB 更新検知→再ルーティング |
| 6 | test_full_pipeline_mock | 全パイプライン mock E2E |

### 6-2. Web 統合

| # | テストケース | 概要 |
|---|------------|------|
| 1 | test_web_import_review_export_flow | インポート→レビュー→エクスポート |
| 2 | test_web_pipeline_creates_db_run | パイプライン結果の DB 登録 |
| 3 | test_web_config_affects_pipeline | 設定変更がパイプラインに反映 |

---

## 実装優先順位

```
Phase 1 (CLI + Config)     → 約22テスト  ... 基盤の信頼性確保
Phase 2 (新カテゴリ)        → 約12テスト  ... 今回のフィクスチャ刷新の検証
Phase 3 (Web API)           → 約23テスト  ... プロダクション品質
Phase 4 (エラーハンドリング)  → 約16テスト  ... 堅牢性
Phase 5 (エッジケース)       → 約14テスト  ... 防御的テスト
Phase 6 (統合テスト)         → 約 9テスト  ... エージェント間連携
────────────────────────────────────────────
合計                         → 約96テスト追加 (86 → 182テスト)
```

## 技術メモ

- CLI テストは `subprocess` or `unittest.mock.patch("sys.argv")` で実装
- Web API テストは `httpx.AsyncClient` + `TestClient` (FastAPI)
- Pipeline テストは `threading.Event` で同期制御
- 全 LLM 呼び出しは `unittest.mock.patch("anthropic.Anthropic")` で mock
- **Python 3.9 制約**: `Optional[X]` を使用、`X | None` 不可
