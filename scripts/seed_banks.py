"""銀行マスタ・QAファイル名のシードデータ登録スクリプト."""

from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path

from src.web import db

SEED_DATA: list[tuple[str, list[str]]] = [
    ("三菱UFJ信託銀行", ["ASPクラウド台帳兼リスク評価シート", "クラウド委託チェックリスト"]),
    ("きらぼし銀行", ["システムリスク評価シート"]),
    ("イオン銀行", ["バックアップに関する状況調査"]),
    ("北國銀行", ["委託先アンケート等"]),
    ("横浜銀行", ["業務の委託（サービス利用）に関するアンケート"]),
    ("福井銀行", ["受託業務にかかる個人情報等の取扱状況に関する回答書等"]),
    ("SBI新生銀行", ["安全管理措置実施状況確認表等", "セキュリティチェックシート"]),
    ("百五銀行", ["顧客データ等委託先チェックリスト"]),
    ("秋田銀行", ["顧客情報等の取扱状況に関する調査票兼回答書"]),
    ("神奈川銀行", ["外部サービス利用型チェックリスト"]),
    ("大分銀行", ["情報セキュリティに関するアンケート"]),
    ("東京スター銀行", ["CSSA対応状況ヒアリングシート"]),
    ("あおぞら銀行", ["オフショア開発チェックシート"]),
    ("西京銀行", ["委託先顧客保護管理態勢に関するアンケート"]),
    ("岩手銀行", ["個人データ安全管理体制に関する確認書等"]),
    ("千葉銀行", ["個人情報の取扱いに関する報告等", "脆弱性評価シート等"]),
    ("京都中央信用金庫", ["顧客情報の安全管理に係る整備状況に関するアンケート", "サイバーセキュリティリスク評価"]),
    ("池田泉州銀行", ["情報システム台帳等"]),
    ("但馬銀行", ["システム監査チェックシート"]),
    ("東日本銀行", ["業務の委託に関するアンケート"]),
    ("静岡銀行", ["業務委託に関する書式集等"]),
    ("播州信用金庫", ["個人情報の取扱に関する報告書"]),
    ("山梨中央銀行", ["サイバーセキュリティ管理状況についてのアンケート"]),
    ("第四北越銀行", ["業務の委託に関するアンケート"]),
    ("群馬銀行", ["委託業務に関する確認シート"]),
]


def seed_banks(db_path: Path) -> dict:
    """銀行とQAファイル名をDBに登録する。既存データはスキップ（冪等）。"""
    db.init_db(db_path)
    created_banks = 0
    skipped_banks = 0
    created_files = 0

    for i, (bank_name, qa_files) in enumerate(SEED_DATA, 1):
        code = f"BANK{i:03d}"
        try:
            bank_id = db.create_bank(db_path, bank_name, code)
            created_banks += 1
        except sqlite3.IntegrityError:
            skipped_banks += 1
            banks = db.list_banks(db_path)
            bank_id = next(b["id"] for b in banks if b["name"] == bank_name)

        existing = db.list_bank_qa_files(db_path, bank_id)
        existing_names = {f["qa_file_name"] for f in existing}
        for qa_file_name in qa_files:
            if qa_file_name not in existing_names:
                try:
                    db.create_bank_qa_file(db_path, bank_id, qa_file_name)
                    created_files += 1
                except sqlite3.IntegrityError:
                    pass  # already exists

    return {
        "created_banks": created_banks,
        "skipped_banks": skipped_banks,
        "created_files": created_files,
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="銀行マスタのシードデータ登録")
    parser.add_argument("--db-path", type=Path, default=db.DEFAULT_DB_PATH)
    args = parser.parse_args()

    result = seed_banks(args.db_path)
    print(
        f"完了: 銀行 {result['created_banks']}件作成, "
        f"{result['skipped_banks']}件スキップ, "
        f"QAファイル {result['created_files']}件作成"
    )
