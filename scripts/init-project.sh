#!/bin/bash
set -e

# カラー定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# スクリプトのディレクトリを取得
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 使用方法
usage() {
    echo "Usage: $0 <project-name>"
    echo ""
    echo "izanagiをベースに新規プロジェクトを初期化します。"
    echo ""
    echo "Example:"
    echo "  $0 my-awesome-poc"
    exit 1
}

# 引数チェック
if [ -z "$1" ]; then
    usage
fi

PROJECT_NAME="$1"
PROJECT_NAME_LOWER=$(echo "$PROJECT_NAME" | tr '[:upper:]' '[:lower:]')
LOGO_LETTER=$(echo "$PROJECT_NAME" | cut -c1 | tr '[:lower:]' '[:upper:]')

echo -e "${GREEN}[INFO]${NC} Initializing project: ${PROJECT_NAME}"
echo ""

# 変更対象ファイル
FILES=(
    "frontend/package.json"
    "backend/app/config.py"
    ".env.example"
    "frontend/index.html"
    "frontend/src/components/app-sidebar.tsx"
    "frontend/src/pages/LoginPage.tsx"
)

# 各ファイルの置換処理
echo -e "${GREEN}[INFO]${NC} Replacing project name..."

# frontend/package.json
sed -i '' "s/\"name\": \"izanagi-frontend\"/\"name\": \"${PROJECT_NAME_LOWER}-frontend\"/" "$PROJECT_ROOT/frontend/package.json"
echo "  - frontend/package.json"

# backend/app/config.py
sed -i '' "s|projects/izanagi/secrets|projects/${PROJECT_NAME_LOWER}/secrets|" "$PROJECT_ROOT/backend/app/config.py"
echo "  - backend/app/config.py"

# .env.example
sed -i '' "s/# izanagi/# ${PROJECT_NAME}/" "$PROJECT_ROOT/.env.example"
sed -i '' "s/GOOGLE_CLOUD_PROJECT=izanagi-dev/GOOGLE_CLOUD_PROJECT=${PROJECT_NAME_LOWER}-dev/" "$PROJECT_ROOT/.env.example"
echo "  - .env.example"

# frontend/index.html
sed -i '' "s|<title>izanagi</title>|<title>${PROJECT_NAME}</title>|" "$PROJECT_ROOT/frontend/index.html"
echo "  - frontend/index.html"

# frontend/src/components/app-sidebar.tsx
sed -i '' "s/>izanagi</>$PROJECT_NAME</" "$PROJECT_ROOT/frontend/src/components/app-sidebar.tsx"
sed -i '' "s/>I</>$LOGO_LETTER</" "$PROJECT_ROOT/frontend/src/components/app-sidebar.tsx"
echo "  - frontend/src/components/app-sidebar.tsx"

# frontend/src/pages/LoginPage.tsx
sed -i '' "s/>izanagi</>$PROJECT_NAME</" "$PROJECT_ROOT/frontend/src/pages/LoginPage.tsx"
sed -i '' "s/>I</>$LOGO_LETTER</" "$PROJECT_ROOT/frontend/src/pages/LoginPage.tsx"
echo "  - frontend/src/pages/LoginPage.tsx"

# CLAUDE.md
sed -i '' "s/# izanagi - /# ${PROJECT_NAME} - /" "$PROJECT_ROOT/CLAUDE.md"
sed -i '' "s/izanagiは/${PROJECT_NAME}は/" "$PROJECT_ROOT/CLAUDE.md"
sed -i '' "s/^izanagi\//${PROJECT_NAME}\//" "$PROJECT_ROOT/CLAUDE.md"
echo "  - CLAUDE.md"

# scripts/dev.sh
sed -i '' "s/# izanagi Development/# ${PROJECT_NAME} Development/" "$PROJECT_ROOT/scripts/dev.sh"
sed -i '' "s/--project=izanagi-dev/--project=${PROJECT_NAME_LOWER}-dev/" "$PROJECT_ROOT/scripts/dev.sh"
sed -i '' "s|/tmp/izanagi-|/tmp/${PROJECT_NAME_LOWER}-|g" "$PROJECT_ROOT/scripts/dev.sh"
sed -i '' "s/=== izanagi Development/=== ${PROJECT_NAME} Development/" "$PROJECT_ROOT/scripts/dev.sh"
echo "  - scripts/dev.sh"

echo ""

# .envファイルの作成
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${GREEN}[INFO]${NC} Creating .env from .env.example..."
    cp "$PROJECT_ROOT/.env.example" "$PROJECT_ROOT/.env"
else
    echo -e "${YELLOW}[WARN]${NC} .env already exists, skipping copy"
fi

echo ""

# Backend setup
echo -e "${GREEN}[INFO]${NC} Setting up backend..."
cd "$PROJECT_ROOT/backend"

# Python実行コマンドの検出（python3を優先）
PYTHON=$(command -v python3 || command -v python)
if [ -z "$PYTHON" ]; then
    echo -e "${RED}[ERROR]${NC} Python not found. Please install Python 3."
    exit 1
fi

$PYTHON -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
echo -e "${GREEN}[INFO]${NC} Backend setup complete"

echo ""

# Frontend setup
echo -e "${GREEN}[INFO]${NC} Setting up frontend..."
cd "$PROJECT_ROOT/frontend"
npm install
echo -e "${GREEN}[INFO]${NC} Frontend setup complete"

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Project initialized successfully!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "Next steps:"
echo "  1. cd $(basename "$PROJECT_ROOT")"
echo "  2. ./scripts/dev.sh start"
echo "  3. Open http://localhost:5173"
echo ""
