# FISC-QAv2 テスト手順書

## 前提条件

- Python 3.9+
- 依存パッケージがインストール済み

```bash
pip install -e ".[dev]"
```

## テスト全体構成

| ファイル | 内容 | テスト数 |
|---------|------|---------|
| `tests/test_web.py` | DB・API単体テスト | ~99 |
| `tests/test_matcher.py` | マッチングロジック | ~10 |
| `tests/test_reader.py` | Reader エージェント | ~10 |
| `tests/test_orchestrator.py` | Orchestrator | ~5 |
| `tests/test_indexer.py` | Indexer エージェント | ~5 |
| `tests/test_router.py` | Router エージェント | ~8 |
| `tests/test_reviewer.py` | Reviewer エージェント | ~5 |
| `tests/test_e2e_workflow.py` | **5ステップワークフローE2E** | **8** |
| `tests/test_e2e.py` | 本番API E2E（API Key必要） | 1 (slow) |

## E2Eワークフローテスト

### 概要

`tests/test_e2e_workflow.py` は5ステップワークフローの統合テストです。3つのテストクラスで構成されます:

- **TestWorkflowXlsx** — XLSX形式での全ステップテスト
- **TestWorkflowDocx** — DOCX形式での全ステップテスト
- **TestFormatParity** — XLSX/DOCXで同一結果になることの検証

### テストシナリオ

| シナリオ | 対象ステップ | 検証内容 |
|---------|-------------|---------|
| 過去回答マッチング | Step2 | 過去Q&Aとのコサイン類似度マッチ → 採用 |
| 共通回答マッチング | Step3 | 共通回答DBとのLLMマッチ → 採用 |
| AI回答生成 | Step4 | KB文書からの回答生成 |
| 全体フロー | Step1→5 | 全ステップ通し + finalize + export |
| フォーマット同一性 | Step1 | XLSX/DOCXで同一質問が抽出される |
| エクスポート形式 | Step5 | 入力形式に応じた出力形式の確認 |

### テストデータ

テストデータは `tests/fixtures/e2e_workflow/` に格納:

| ファイル | 内容 |
|---------|------|
| `questionnaire_10q.xlsx` | 質問票（XLSX, 10問） |
| `questionnaire_10q.docx` | 質問票（DOCX, 10問） |
| `past_answers.json` | 過去回答（5件） |
| `common_answers.json` | 共通回答（3件） |

質問10問の内訳:
- Q1-Q5: 過去回答マッチ対象（類似度 >= 0.7）
- Q6-Q8: 共通回答マッチ対象（LLMマッチ）
- Q9-Q10: KB生成対象（新規質問）

### テストデータの再生成

```bash
python3 tests/fixtures/e2e_workflow/generate_e2e_fixtures.py
```

### Mock方針

| ステップ | Mock対象 | 理由 |
|---------|---------|------|
| Step2 | なし（実コサイン類似度計算） | API不要 |
| Step3 | `litellm.completion` | LLM API呼び出し回避 |
| Step4 | `pipeline.start_session_pipeline_job` | AI生成パイプライン回避 |

## テスト実行手順

### 1. E2Eワークフローテストのみ

```bash
python3 -m pytest tests/test_e2e_workflow.py -v
```

### 2. 全テスト（本番API E2E除く）

```bash
python3 -m pytest tests/ -v --ignore=tests/test_e2e.py
```

### 3. 特定シナリオのみ

```bash
# XLSX過去回答マッチング
python3 -m pytest tests/test_e2e_workflow.py::TestWorkflowXlsx::test_step2_matches_past_answers -v

# DOCX全体フロー
python3 -m pytest tests/test_e2e_workflow.py::TestWorkflowDocx::test_full_workflow_docx -v

# フォーマット同一性
python3 -m pytest tests/test_e2e_workflow.py::TestFormatParity -v
```

### 4. 本番API E2Eテスト（API Key必要）

```bash
# ANTHROPIC_API_KEY または FISC_API_KEY を設定して実行
FISC_API_KEY=sk-xxx python3 -m pytest tests/test_e2e.py -v
```

## 期待結果

全テストが `PASSED` になること:

```
tests/test_e2e_workflow.py::TestWorkflowXlsx::test_step2_matches_past_answers PASSED
tests/test_e2e_workflow.py::TestWorkflowXlsx::test_step3_matches_common_answers PASSED
tests/test_e2e_workflow.py::TestWorkflowXlsx::test_step4_generates_from_kb PASSED
tests/test_e2e_workflow.py::TestWorkflowXlsx::test_full_workflow_end_to_end PASSED
tests/test_e2e_workflow.py::TestWorkflowDocx::test_step1_extracts_questions_from_docx PASSED
tests/test_e2e_workflow.py::TestWorkflowDocx::test_full_workflow_docx PASSED
tests/test_e2e_workflow.py::TestFormatParity::test_same_questions_extracted PASSED
tests/test_e2e_workflow.py::TestFormatParity::test_export_formats PASSED
```

## トラブルシューティング

### テストデータが見つからない
```bash
python3 tests/fixtures/e2e_workflow/generate_e2e_fixtures.py
```

### `ModuleNotFoundError: No module named 'src'`
プロジェクトルートで `pip install -e .` を実行してください。

### Step2マッチングが失敗する
過去回答の質問文とテスト質問票の質問文のコサイン類似度が0.7未満の場合に発生します。`tests/fixtures/e2e_workflow/generate_e2e_fixtures.py` の質問文を調整してください。
