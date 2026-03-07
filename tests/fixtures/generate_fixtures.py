"""FISC-QAv2 テストフィクスチャ生成スクリプト

ダミーの PDF / DOCX / Excel ファイルを一括生成する。
  python tests/fixtures/generate_fixtures.py
"""

from __future__ import annotations

import json
from pathlib import Path

from docx import Document
from openpyxl import Workbook
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

# ---------------------------------------------------------------------------
# パス定義
# ---------------------------------------------------------------------------
FIXTURES = Path(__file__).resolve().parent
INPUT_DIR = FIXTURES / "input"
KB_DIR = FIXTURES / "kb"
EXPECTED_DIR = FIXTURES / "expected"

POLICIES_DIR = KB_DIR / "policies"
PAST_ANSWERS_DIR = KB_DIR / "past_answers"
SYSTEM_DOCS_DIR = KB_DIR / "system_docs"

ALL_DIRS = [INPUT_DIR, POLICIES_DIR, PAST_ANSWERS_DIR, SYSTEM_DOCS_DIR, EXPECTED_DIR]

# ---------------------------------------------------------------------------
# 日本語フォント登録（macOS 標準ヒラギノ / フォールバック）
# ---------------------------------------------------------------------------
_JP_FONT_NAME = "IPAGothic"
_JP_FONT_REGISTERED = False

_CANDIDATE_FONTS = [
    "/System/Library/Fonts/ヒラギノ角ゴシック W3.ttc",
    "/System/Library/Fonts/Hiragino Sans GB W3.otf",
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/usr/share/fonts/truetype/ipafont-gothic/ipag.ttf",
    "/usr/share/fonts/opentype/ipafont-gothic/ipag.ttf",
]


def _register_jp_font() -> str:
    """日本語フォントを登録して使用可能なフォント名を返す。"""
    global _JP_FONT_REGISTERED, _JP_FONT_NAME
    if _JP_FONT_REGISTERED:
        return _JP_FONT_NAME
    for fp in _CANDIDATE_FONTS:
        p = Path(fp)
        if p.exists():
            try:
                pdfmetrics.registerFont(TTFont(_JP_FONT_NAME, str(p)))
                _JP_FONT_REGISTERED = True
                return _JP_FONT_NAME
            except Exception:
                continue
    # フォールバック: Helvetica（日本語は化けるが生成は成功する）
    _JP_FONT_NAME = "Helvetica"
    _JP_FONT_REGISTERED = True
    return _JP_FONT_NAME


# =========================================================================
# PDF 生成
# =========================================================================

def _make_pdf(path: Path, title: str, sections: list[tuple[str, str]], target_pages: int = 6):
    """ReportLab で日本語テキスト入りの PDF を生成する。"""
    font_name = _register_jp_font()
    doc = SimpleDocTemplate(str(path), pagesize=A4,
                            topMargin=20 * mm, bottomMargin=20 * mm)
    styles = {
        "title": ParagraphStyle("title", fontName=font_name, fontSize=16, leading=22,
                                spaceAfter=12),
        "heading": ParagraphStyle("heading", fontName=font_name, fontSize=13, leading=18,
                                  spaceAfter=8, spaceBefore=12),
        "body": ParagraphStyle("body", fontName=font_name, fontSize=10, leading=15,
                               spaceAfter=6),
    }

    story: list = []
    story.append(Paragraph(title, styles["title"]))
    story.append(Spacer(1, 6 * mm))

    # セクションを繰り返してページ数を稼ぐ
    repeat = max(1, target_pages // max(len(sections), 1))
    for _ in range(repeat):
        for heading, body in sections:
            story.append(Paragraph(heading, styles["heading"]))
            for para in body.split("\n\n"):
                story.append(Paragraph(para.replace("\n", "<br/>"), styles["body"]))
            story.append(Spacer(1, 3 * mm))

    doc.build(story)


# =========================================================================
# DOCX 生成
# =========================================================================

def _make_docx(path: Path, title: str, sections: list[tuple[str, str]]):
    doc = Document()
    doc.add_heading(title, level=0)
    for heading, body in sections:
        doc.add_heading(heading, level=1)
        for para in body.split("\n\n"):
            doc.add_paragraph(para)
    doc.save(str(path))


# =========================================================================
# Excel 生成
# =========================================================================

def _make_excel(path: Path, headers: list[str], rows: list[list], sheet_name: str = "Sheet1"):
    wb = Workbook()
    ws = wb.active
    ws.title = sheet_name
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(str(path))


# =========================================================================
# コンテンツ定義
# =========================================================================

# ---------- 質問データ (20問 — 実際のFISCアンケート形式) ----------
# 列: No., 大分類, 小分類, 質問内容, 回答, 対応状況, 根拠ソース, 確信度, 備考

QUESTIONS: list[dict] = [
    {"no": 1, "major": "セキュリティ管理", "minor": "ポリシー管理",
     "question": "情報セキュリティポリシーを策定・文書化していますか？また、定期的に見直しを行っていますか？"},
    {"no": 2, "major": "セキュリティ管理", "minor": "組織体制",
     "question": "情報セキュリティの責任者（CISO等）を任命し、責任・権限を明確にしていますか？"},
    {"no": 3, "major": "アクセス管理", "minor": "ユーザー認証",
     "question": "システムへのアクセスにはID・パスワードによる認証を実施していますか？パスワードの複雑性要件はありますか？"},
    {"no": 4, "major": "アクセス管理", "minor": "権限管理",
     "question": "ユーザーの権限は業務上必要最小限の範囲に制限されていますか？（最小権限の原則）"},
    {"no": 5, "major": "アクセス管理", "minor": "特権アカウント",
     "question": "管理者権限（特権アカウント）の利用は制限・記録されていますか？"},
    {"no": 6, "major": "ウイルス対策", "minor": "マルウェア対策",
     "question": "サーバー・クライアント端末にウイルス対策ソフトを導入していますか？定義ファイルの更新頻度はどうなっていますか？"},
    {"no": 7, "major": "ウイルス対策", "minor": "不正プログラム",
     "question": "外部記憶媒体（USBメモリ等）の利用制限はありますか？"},
    {"no": 8, "major": "ネットワーク管理", "minor": "境界防御",
     "question": "インターネットとの接続にはファイアウォールを設置していますか？また、不要なポートは閉鎖されていますか？"},
    {"no": 9, "major": "ネットワーク管理", "minor": "通信暗号化",
     "question": "外部との通信にはTLS等の暗号化プロトコルを使用していますか？"},
    {"no": 10, "major": "ネットワーク管理", "minor": "不正侵入検知",
     "question": "IDS/IPS（不正侵入検知・防止システム）を導入していますか？"},
    {"no": 11, "major": "バックアップ管理", "minor": "バックアップ",
     "question": "重要データのバックアップはどのような頻度・方式で実施していますか？"},
    {"no": 12, "major": "バックアップ管理", "minor": "復旧テスト",
     "question": "バックアップデータからの復旧テストを定期的に実施していますか？"},
    {"no": 13, "major": "インシデント対応", "minor": "対応手順",
     "question": "セキュリティインシデントが発生した場合の対応手順（インシデントレスポンス計画）はありますか？"},
    {"no": 14, "major": "インシデント対応", "minor": "報告体制",
     "question": "インシデント発生時の上長・関係機関への報告体制はありますか？"},
    {"no": 15, "major": "変更管理", "minor": "変更手順",
     "question": "システムの変更（パッチ適用・設定変更等）に際して、変更管理手順を定めていますか？"},
    {"no": 16, "major": "変更管理", "minor": "脆弱性管理",
     "question": "OSやミドルウェアのセキュリティパッチは定期的に適用していますか？"},
    {"no": 17, "major": "物理セキュリティ", "minor": "入退室管理",
     "question": "サーバー室等の機密エリアへの入退室管理（ICカード等）を実施していますか？"},
    {"no": 18, "major": "物理セキュリティ", "minor": "設備管理",
     "question": "サーバー室の空調・電源・消火設備は整備されていますか？"},
    {"no": 19, "major": "教育・訓練", "minor": "セキュリティ教育",
     "question": "従業員に対して情報セキュリティ教育を定期的に実施していますか？"},
    {"no": 20, "major": "教育・訓練", "minor": "標的型攻撃訓練",
     "question": "フィッシングメール等の標的型攻撃を想定した訓練を実施していますか？"},
]

NUM_QUESTIONS = len(QUESTIONS)

# 大分類→KBソースの対応マップ（Router期待出力用）
_MAJOR_TO_SOURCES: dict[str, list[str]] = {
    "セキュリティ管理": ["policies/security_policy.pdf", "past_answers/past_answer_2024.xlsx"],
    "アクセス管理": ["policies/access_control_policy.pdf", "policies/security_policy.pdf"],
    "ウイルス対策": ["policies/security_policy.pdf", "system_docs/operation_manual.pdf"],
    "ネットワーク管理": ["system_docs/infra_overview.pdf", "policies/encryption_standards.pdf"],
    "バックアップ管理": ["system_docs/dr_bcp_plan.pdf", "system_docs/infra_overview.pdf"],
    "インシデント対応": ["system_docs/incident_response.docx", "system_docs/operation_manual.pdf"],
    "変更管理": ["system_docs/operation_manual.pdf", "system_docs/audit_compliance.docx"],
    "物理セキュリティ": ["system_docs/infra_overview.pdf", "policies/security_policy.pdf"],
    "教育・訓練": ["system_docs/audit_compliance.docx", "policies/security_policy.pdf"],
}

# ---------- KB コンテンツ ----------

POLICY_FILES = {
    "security_policy.pdf": {
        "title": "情報セキュリティポリシー",
        "pages": 9,
        "sections": [
            ("1. 目的", "本ポリシーは、当社の情報資産を保護するための基本方針を定めるものである。\n\n金融機関として、FISC安全対策基準に準拠し、情報セキュリティの維持・向上を図る。"),
            ("2. パスワードポリシー", "パスワードは最低12文字以上とし、大文字・小文字・数字・記号を含むこと。\n\nパスワードの有効期限は90日とし、過去12世代のパスワードの再利用を禁止する。\n\n5回連続の認証失敗でアカウントをロックアウトし、30分後に自動解除する。"),
            ("3. 多要素認証（MFA）", "重要システムへのアクセスには多要素認証を必須とする。\n\n利用可能な認証要素: ハードウェアトークン、ソフトウェアトークン（TOTP）、生体認証。\n\nSMS認証は推奨されないが、他の手段が利用できない場合に限り許容する。"),
            ("4. アカウント管理", "共有アカウントの使用は原則禁止とする。やむを得ず使用する場合は、CISO承認のうえ利用記録を取得する。\n\n初期パスワードは初回ログイン時に変更を強制する。\n\nサービスアカウントは個別に管理し、定期的にパスワードをローテーションする。"),
            ("5. 認証ログ管理", "認証に関するすべてのイベント（成功・失敗）をログに記録する。\n\nログの保管期間は最低1年間とし、改ざん防止措置を講じる。\n\n月次でログのレビューを実施し、不正アクセスの兆候を検知する。"),
        ],
    },
    "access_control_policy.pdf": {
        "title": "アクセス制御ポリシー",
        "pages": 7,
        "sections": [
            ("1. 基本方針", "最小権限の原則に基づき、業務に必要な最低限のアクセス権のみを付与する。\n\n職務分掌を考慮し、利益相反が生じるアクセス権の兼務を禁止する。"),
            ("2. 権限管理", "役割ベースのアクセス制御（RBAC）を採用し、職位・部署に応じたロールを定義する。\n\nアクセス権の付与・変更・削除は、申請→承認→実施→確認のワークフローに従う。\n\n特権アカウントは必要最小限とし、利用時はジャストインタイム（JIT）アクセスを採用する。"),
            ("3. 定期棚卸し", "四半期ごとにアクセス権限の棚卸しを実施する。\n\n不要な権限を検出した場合は速やかに削除する。\n\n棚卸し結果は部門長が承認し、記録を3年間保管する。"),
            ("4. 退職・異動時の対応", "退職日当日にすべてのアカウントを無効化する。\n\n異動時は旧部署の権限を削除し、新部署の権限を付与する。\n\n外部委託先の契約終了時も同様に即日無効化する。"),
        ],
    },
    "encryption_standards.pdf": {
        "title": "暗号化基準",
        "pages": 5,
        "sections": [
            ("1. 暗号化方式", "保存データ: AES-256-GCM を標準とする。\n\n通信暗号化: TLS 1.2 以上を必須とし、TLS 1.0/1.1 は無効化する。\n\n証明書: 2048bit 以上の RSA、または ECC P-256 以上を使用する。"),
            ("2. 鍵管理", "暗号鍵はHSM（Hardware Security Module）で生成・保管する。\n\n鍵のローテーション周期は年1回とする。\n\n鍵の廃棄時は暗号学的に安全な方法で消去する。"),
            ("3. 適用範囲", "個人情報、認証情報、金融取引データは必ず暗号化する。\n\nバックアップデータも同等の暗号化レベルを適用する。"),
        ],
    },
    "data_protection_policy.docx": {
        "title": "データ保護ポリシー",
        "sections": [
            ("1. データ分類", "機密（Confidential）: 個人情報、認証情報、経営戦略情報\n\n社外秘（Internal）: 業務マニュアル、社内通達、組織図\n\n公開（Public）: プレスリリース、公開Webサイト掲載情報"),
            ("2. 保持期間", "取引データ: 法定保持期間（10年）\n\n個人情報: 利用目的達成後、速やかに廃棄\n\nログデータ: 最低1年、監査要件に応じて最大7年"),
            ("3. 廃棄方法", "電子データ: 暗号学的消去または物理破壊\n\n紙媒体: シュレッダー（クロスカット以上）\n\n外部委託による廃棄時は廃棄証明書を取得する。"),
        ],
    },
    "remote_access_policy.docx": {
        "title": "リモートアクセスポリシー",
        "sections": [
            ("1. VPN要件", "リモートアクセスには会社承認のVPNクライアントを使用すること。\n\nVPN接続時は多要素認証を必須とする。\n\nスプリットトンネリングは禁止する。"),
            ("2. BYOD管理", "個人端末の業務利用は原則禁止とする。\n\nやむを得ず利用する場合はMDM（Mobile Device Management）を導入すること。\n\n紛失・盗難時のリモートワイプ機能を有効にすること。"),
            ("3. テレワーク時の注意事項", "公共Wi-Fiでの業務は禁止する。\n\n画面ロックは5分以内に自動設定すること。\n\n業務データの個人クラウドストレージへの保存を禁止する。"),
        ],
    },
}

SYSTEM_DOC_FILES = {
    "infra_overview.pdf": {
        "title": "インフラ構成概要",
        "pages": 9,
        "sections": [
            ("1. 全体構成", "本システムはハイブリッドクラウド構成を採用している。\n\n基幹系システム: オンプレミスデータセンター（東京DC・大阪DC）に配置。\n\n情報系システム: AWS東京リージョン（ap-northeast-1）に配置。\n\nDMZ: WAF + ロードバランサーによるトラフィック制御。"),
            ("2. ネットワーク構成", "インターネット接続: 冗長化されたISP回線（2系統）。\n\nDC間接続: 専用線（10Gbps）による冗長接続。\n\nセグメント分離: 本番環境・開発環境・管理環境を論理的に分離。\n\nファイアウォール: ゾーンベースポリシーを適用。"),
            ("3. サーバ構成", "Webサーバ: Nginx（4台構成、Active-Active）。\n\nAPサーバ: Kubernetes クラスタ（3ノード）。\n\nDBサーバ: PostgreSQL（プライマリ + スタンバイ、同期レプリケーション）。\n\n監視サーバ: Prometheus + Grafana。"),
            ("4. クラウド構成", "コンピュート: EC2（Auto Scaling Group）/ ECS Fargate。\n\nストレージ: S3（暗号化有効、バージョニング有効）。\n\nデータベース: RDS PostgreSQL（Multi-AZ）。\n\nCDN: CloudFront + WAF。"),
        ],
    },
    "dr_bcp_plan.pdf": {
        "title": "DR・BCP計画",
        "pages": 7,
        "sections": [
            ("1. 目的", "自然災害、システム障害等の不測の事態に備え、事業継続性を確保する。\n\nFISC安全対策基準の可用性要件に準拠する。"),
            ("2. RTO / RPO", "基幹系システム: RTO = 4時間、RPO = 1時間。\n\n情報系システム: RTO = 8時間、RPO = 4時間。\n\n外部公開システム: RTO = 2時間、RPO = 15分。"),
            ("3. バックアップ方式", "日次フルバックアップ（毎日 02:00 JST）。\n\n1時間ごとの差分バックアップ。\n\nバックアップ先: オンサイト（高速リストア用）+ 遠隔地（DR用）。\n\n保管期間: 日次=30日、週次=12週、月次=12ヶ月。"),
            ("4. DR訓練", "年2回のDR切替訓練を実施する。\n\n訓練結果を文書化し、改善点を次回計画に反映する。\n\nリストアテストは四半期ごとに実施する。"),
        ],
    },
    "operation_manual.pdf": {
        "title": "運用管理マニュアル",
        "pages": 8,
        "sections": [
            ("1. 監視体制", "24時間365日の有人監視体制を維持する。\n\n監視対象: CPU使用率、メモリ使用率、ディスク使用率、ネットワークトラフィック、アプリケーションレスポンスタイム。\n\nアラート閾値: Warning = 70%、Critical = 90%。"),
            ("2. ログ管理", "取得対象: OS、ミドルウェア、アプリケーション、セキュリティ機器のログ。\n\n集約先: SIEM（Splunk）に集約し、リアルタイム分析を行う。\n\n保管期間: 通常ログ = 1年、セキュリティログ = 3年。\n\nログの改ざん防止: Write Once ストレージに保管。"),
            ("3. 変更管理", "すべてのシステム変更はCAB（Change Advisory Board）の承認を要する。\n\n緊急変更は事後承認を認めるが、24時間以内に文書化する。\n\nリリース手順: 開発→検証→ステージング→本番の4段階。"),
            ("4. パッチ管理", "セキュリティパッチは公開後14日以内に検証を開始する。\n\n重大な脆弱性（CVSS 9.0以上）は72時間以内に対応する。\n\nパッチ適用結果を記録し、ロールバック手順を確保する。"),
        ],
    },
    "incident_response.docx": {
        "title": "インシデント対応手順",
        "sections": [
            ("1. インシデント分類", "レベル1（重大）: 個人情報漏洩、不正アクセス、ランサムウェア感染。\n\nレベル2（中程度）: マルウェア検知、不審な通信検知、権限昇格試行。\n\nレベル3（軽微）: ポリシー違反、設定ミス、軽微な可用性低下。"),
            ("2. エスカレーション", "レベル1: 検知→CSIRT→CISO→経営層（30分以内）。金融庁への報告を検討。\n\nレベル2: 検知→CSIRT→情報セキュリティ部門長（1時間以内）。\n\nレベル3: 検知→運用チーム→情報セキュリティ部門（翌営業日）。"),
            ("3. 対応フロー", "検知・初期対応 → 封じ込め → 根本原因分析 → 復旧 → 再発防止策策定 → 報告書作成。\n\nフォレンジック調査が必要な場合は外部専門機関と連携する。"),
            ("4. 報告義務", "個人情報漏洩時は個人情報保護委員会への報告を行う。\n\n金融庁・JPCERT/CCへの報告基準に従い適時報告する。"),
        ],
    },
    "audit_compliance.docx": {
        "title": "監査・コンプライアンス管理",
        "sections": [
            ("1. 内部監査", "年1回の定期内部監査を実施する。\n\n監査対象: 情報セキュリティ管理態勢、アクセス管理、変更管理、インシデント対応。\n\n監査結果は取締役会に報告する。"),
            ("2. 外部監査", "SOC2 Type II 監査を年1回受審する。\n\nFISC安全対策基準への準拠状況を外部評価機関が検証する。\n\n指摘事項は90日以内に改善計画を策定し、是正する。"),
            ("3. 証跡管理", "監査証跡は改ざん防止措置を施したストレージに保管する。\n\n保管期間は最低5年とする。\n\n証跡へのアクセスは監査部門に限定する。"),
        ],
    },
}

# ---------- 過去回答データ ----------

def _generate_past_answers(year: int, num_questions: int) -> list[list]:
    rows = []
    sample_answers = [
        ("実施している", "セキュリティポリシーに基づき実施。年次レビューを実施。", "高"),
        ("一部実施している", "主要システムには適用済み。レガシーシステムは対応中。", "中"),
        ("実施している", "規程に基づき運用中。四半期ごとにレビュー。", "高"),
        ("計画中", "次年度に導入予定。ベンダー選定中。", "低"),
        ("実施している", "全システムに適用済み。自動化ツールで管理。", "高"),
    ]
    for i in range(1, num_questions + 1):
        ans = sample_answers[(i - 1) % len(sample_answers)]
        rows.append([f"Q{i:03d}", ans[0], ans[1], f"{year}年度対応", ans[2]])
    return rows


# =========================================================================
# メイン生成関数
# =========================================================================

def generate_all():
    print("=== FISC-QAv2 テストフィクスチャ生成 ===\n")

    # ディレクトリ作成
    for d in ALL_DIRS:
        d.mkdir(parents=True, exist_ok=True)

    # --- 1. 入力ファイル: questionnaire.xlsx (回答欄は空) ---
    print("[1/6] questionnaire.xlsx ...")
    headers = ["No.", "大分類", "小分類", "質問内容", "回答", "対応状況", "根拠ソース", "確信度", "備考"]
    rows = [[q["no"], q["major"], q["minor"], q["question"], "", "", "", "", ""]
            for q in QUESTIONS]
    _make_excel(INPUT_DIR / "questionnaire.xlsx", headers, rows, sheet_name="FISC回答結果")

    # --- 2. KB: policies ---
    print("[2/6] KB policies ...")
    for fname, meta in POLICY_FILES.items():
        path = POLICIES_DIR / fname
        if fname.endswith(".pdf"):
            _make_pdf(path, meta["title"], meta["sections"], target_pages=meta.get("pages", 6))
        else:
            _make_docx(path, meta["title"], meta["sections"])
        print(f"  -> {path.relative_to(FIXTURES)}")

    # --- 3. KB: system_docs ---
    print("[3/6] KB system_docs ...")
    for fname, meta in SYSTEM_DOC_FILES.items():
        path = SYSTEM_DOCS_DIR / fname
        if fname.endswith(".pdf"):
            _make_pdf(path, meta["title"], meta["sections"], target_pages=meta.get("pages", 6))
        else:
            _make_docx(path, meta["title"], meta["sections"])
        print(f"  -> {path.relative_to(FIXTURES)}")

    # --- 4. KB: past_answers ---
    print("[4/6] KB past_answers ...")
    pa_headers = ["質問ID", "回答", "根拠", "備考", "信頼度"]
    _make_excel(PAST_ANSWERS_DIR / "past_answer_2024.xlsx", pa_headers,
                _generate_past_answers(2024, NUM_QUESTIONS), sheet_name="回答実績")
    _make_excel(PAST_ANSWERS_DIR / "past_answer_2023.xlsx", pa_headers,
                _generate_past_answers(2023, NUM_QUESTIONS), sheet_name="回答実績")
    print("  -> past_answer_2024.xlsx, past_answer_2023.xlsx")

    # --- 5. 期待出力 JSON ---
    print("[5/6] Expected outputs ...")
    _generate_expected_outputs()

    print("\n=== 生成完了 ===")
    print(f"合計ファイル数: {_count_files()}")


def _generate_expected_outputs():
    # index.json
    kb_files = []
    for subdir in ["policies", "past_answers", "system_docs"]:
        d = KB_DIR / subdir
        if d.exists():
            for f in sorted(d.iterdir()):
                if f.is_file():
                    kb_files.append({
                        "file_name": f.name,
                        "path": f"tests/fixtures/kb/{subdir}/{f.name}",
                        "category": subdir,
                        "summary": f"[要約] {f.stem} の内容",
                        "estimated_tokens": 2000,
                    })
    index_path = EXPECTED_DIR / "index.json"
    index_path.write_text(json.dumps(kb_files, ensure_ascii=False, indent=2), encoding="utf-8")

    # routing_map.json
    routing = {}
    for q in QUESTIONS:
        no = q["no"]
        major = q["major"]
        sources = _MAJOR_TO_SOURCES.get(major, [])
        routing[str(no)] = {
            "major": major,
            "minor": q["minor"],
            "assigned_sources": sources,
        }
    routing_path = EXPECTED_DIR / "routing_map.json"
    routing_path.write_text(json.dumps(routing, ensure_ascii=False, indent=2), encoding="utf-8")

    # final_answers.json
    answers = {}
    for q in QUESTIONS:
        no = q["no"]
        answers[str(no)] = {
            "question": q["question"],
            "answer": "",
            "status": "",
            "evidence": "",
            "confidence": "",
            "needs_review": True,
        }
    answers_path = EXPECTED_DIR / "final_answers.json"
    answers_path.write_text(json.dumps(answers, ensure_ascii=False, indent=2), encoding="utf-8")


def _count_files() -> int:
    count = 0
    for d in [INPUT_DIR, POLICIES_DIR, PAST_ANSWERS_DIR, SYSTEM_DOCS_DIR, EXPECTED_DIR]:
        if d.exists():
            count += sum(1 for f in d.iterdir() if f.is_file())
    return count


if __name__ == "__main__":
    generate_all()
