# ハードゲート仕様書 — 判定結果に応じた回答列の出力制御

## 1. 概要

ハードゲートとは、LLMの出力内容に依存せず、**出力層でルールベースに回答列への書き込みを制御する仕組み**である。

### なぜ必要か

FISCアンケートの一部のフォーマット（assessment形式）では、判定結果（○/△/×）に応じて記入すべき列が厳密に決まっている。LLMにプロンプトで「この列にだけ書け」と指示しても、遵守されない場合がある。ハードゲートはこの問題を、LLMの後段で機械的に解決する。

---

## 2. 対象フォーマット

assessment形式の質問票で、**複数の回答列**と**判定列**を持つもの。

```
例: FISC安全管理措置アンケート

| 質問 | 判定 | 対応状況（○の場合） | 代替策（△/×の場合） |
|------|------|---------------------|---------------------|
| ...  | ○    | 実装済み。XXXで対応。 |                     |
| ...  | △    |                     | 2025年Q3に対応予定。 |
| ...  | ×    |                     |                     |
```

- **判定列（judgment）**: ○/△/× の記号
- **回答列0（answer col_0）**: 「対応状況」— ○の場合に記入
- **回答列1（answer col_1）**: 「代替策」— △/×の場合に記入（手動のみ）

---

## 3. ルール定義

| 判定 | col_0（対応状況） | col_1（代替策） |
|------|-------------------|-----------------|
| ○/◎ | AI回答を記入      | **必ず空**（ハードゲート） |
| △    | **必ず空**（ハードゲート） | AI は書かない。ユーザが手動入力した場合のみ出力 |
| ×    | **必ず空**（ハードゲート） | 同上 |
| 空（未判定） | AI回答を記入（フォールバック） | 空 |

### 設計判断

- **△/×の代替策はAIで書かない**: 「代替策や今後のご予定」はクライアント固有の情報であり、AIが生成するとハルシネーションになる。ユーザがStep5で手動入力した場合のみエクスポートに反映される。
- **ハードゲートはLLM出力に関わらず強制**: たとえLLMがcol_1にテキストを返しても、判定が○ならcol_1は必ず空になる。

---

## 4. データモデル

### DB: `session_questions` テーブル

| カラム | 型 | 用途 |
|--------|-----|------|
| `assessment_mark` | TEXT | 判定結果（○/△/×）。Reader LLM の judgment または `judge_assessment_marks` で設定 |
| `answer_texts` | TEXT (JSON) | 列別回答テキスト。`{"D": "対応状況テキスト", "E": "代替策テキスト"}` |
| `answer_text` | TEXT | 主回答テキスト（従来互換。過去回答マッチング・蓄積に使用） |

### answer_texts の役割

- **Pipeline設定時**: judgment に応じて適切な列にのみAI回答を格納
  - ○ → `{"D": "AI回答"}` （col_0のみ）
  - △/× → `{}` （空。AIは代替策を書かない）
- **ユーザ編集時**: Step5 で各列の textarea から保存
  - 例: `{"D": "対応済み", "E": "2025年Q3に予定"}`
- **エクスポート時**: 列別テキストとハードゲートの両方が適用される

---

## 5. 処理フロー

### Pipeline（`src/web/pipeline.py`）

```
Reader LLM → answer + judgment
  ↓
judgment = "○" → answer_texts = {"D": answer}、assessment_mark = "○"
judgment = "△" → answer_texts = {}、assessment_mark = "△"
judgment = "×" → answer_texts = {}、assessment_mark = "×"
  ↓
judge_assessment_marks（全質問に assessment_mark を設定）
  ↓
○ → answer_texts = {"D": answer_text}（col_0にルーティング）
△/× → answer_texts = {}（AIテキストをどの列にもルーティングしない）
```

### Frontend Step5（`frontend/src/pages/SessionStep5Page.tsx`）

```
初期化:
  answer_texts に値あり → そのまま表示
  answer_texts が空 + ○ + col_0 → answer_text をフォールバック
  それ以外 → 空

表示:
  判定に合わない列は opacity-40 で薄く表示（dimmed）

保存:
  各列の textarea テキスト + assessment_mark を PUT /api/sessions/{id}/questions/{no}
  → DB の answer_texts と assessment_mark を更新
```

### Export（`src/file_io.py`）

```
_write_xlsx_answers / _write_docx_answers:

for 各 answer 列:
  ① ハードゲート判定:
     ○ + col_1 → cell = 空（強制）→ continue
     △/× + col_0 → cell = 空（強制）→ continue

  ② テキスト選択:
     per_col_answers あり → col_texts[col] を使用
     per_col_answers なし → answers[no] をフォールバック
       ただし △/× + col_1 → 空（AIで書かない）
```

---

## 6. 実装箇所

| ファイル | 箇所 | 内容 |
|---------|------|------|
| `src/web/db.py` | L148, L190 | `assessment_mark`、`answer_texts` カラム定義 |
| `src/web/pipeline.py` | L232-246 | Reader結果の列別格納 |
| `src/web/pipeline.py` | L253-277 | `judge_assessment_marks` の実行と answer_texts 設定 |
| `src/web/app.py` | L86-90 | `QuestionEdit` モデル（assessment_mark, answer_texts） |
| `src/web/app.py` | L804-810 | `edit_question_answer()` で assessment_mark/answer_texts 保存 |
| `src/web/app.py` | L862-887 | `export_session()` で choices/per_col_answers 構築 |
| `src/file_io.py` | L459-475 | `_write_xlsx_answers()` ハードゲートロジック |
| `src/file_io.py` | L546-558 | `_write_docx_answers()` ハードゲートロジック |
| `frontend/.../SessionStep5Page.tsx` | L109-119 | 初期化（judgment考慮のフォールバック） |
| `frontend/.../SessionStep5Page.tsx` | L140-177 | `saveDraft()` 列別テキスト + assessment_mark 送信 |
| `frontend/.../SessionStep5Page.tsx` | L290-300 | dimmed 表示制御 |
