# FISC-QAv2 - 生成AI PoC雛形環境

## プロダクト概要

FISC-QAv2はステラアイズ株式会社の生成AI PoC雛形環境です。様々なAIユースケースを素早く検証するための基盤を提供します。

### 提供機能
- 認証基盤（Azure AD / MSAL）
- ファイルアップロード・テキスト抽出
- GCP インフラ（Datastore, Cloud Storage, App Engine）

## 開発方針

### ベストプラクティスに従う

- **確立された方法を使う**: 独自のアイデアや創意工夫で実装しない
- **標準的なパターンを優先**: フレームワークやライブラリが提供する方法を使う
- **UIはshadcn/uiを使う**: 独自コンポーネントを作らず、shadcn/uiのコンポーネントを使う

### 最小構成で実装する（YAGNI原則）

- **現時点で必要な機能のみ実装する**
- **過剰設計を避ける**: 将来の要件を見越した抽象化や汎用化は行わない
- **シンプルさを優先**: 3行のコピペは1つの関数より良い場合がある
- **動くものを先に**: 完璧なアーキテクチャより動作するコードを優先

### やらないこと

- 独自の実装パターンの発明
- 使われていないコードの追加
- 「将来使うかもしれない」機能の実装
- 過度なエラーハンドリングやバリデーション
- 不要なドキュメントやコメント

## 技術スタック

| レイヤー | 技術 |
|---------|------|
| Frontend | React 19 + Vite + TypeScript + shadcn/ui + Tailwind CSS v4 |
| Backend | FastAPI + Python 3.11 |
| Database | Google Cloud Datastore (KVS方式) |
| 認証 | Azure AD / MSAL (ホワイトリスト制) |
| Deploy | App Engine Standard |

## ディレクトリ構成

```
FISC-QAv2/
├── CLAUDE.md              # このファイル
├── knowledge/             # 設計ドキュメント
├── config/                # 設定ファイル
├── scripts/               # 開発用スクリプト
│   └── dev.sh            # サービス起動/停止
├── backend/               # FastAPI
│   └── app/
│       ├── main.py
│       ├── config.py
│       ├── dependencies/  # 認証等
│       ├── routers/       # APIエンドポイント
│       ├── repositories/  # データアクセス
│       ├── schemas/       # リクエスト/レスポンス定義
│       └── services/      # ビジネスロジック
└── frontend/              # React + Vite
    └── src/
        ├── components/
        │   └── ui/        # shadcn/ui
        ├── pages/
        ├── hooks/
        └── lib/
```

## 開発環境の起動

### 起動/停止

```bash
# 全サービス起動
./scripts/dev.sh start

# 状態確認
./scripts/dev.sh status

# 全サービス停止
./scripts/dev.sh stop

# 再起動
./scripts/dev.sh restart
```

### サービスURL

| サービス | URL |
|---------|-----|
| Frontend | http://localhost:5173 |
| Backend API | http://localhost:8000 |
| API Docs | http://localhost:8000/docs |
| Datastore Emulator | http://localhost:8081 |

## スタイルガイド

- UIコンポーネント: shadcn/ui (new-york style)
- Font: システムフォント
