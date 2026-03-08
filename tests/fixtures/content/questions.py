"""FISC-QAv2 質問定義 (30問・12カテゴリ)"""
from __future__ import annotations

QUESTIONS: list[dict] = [
    # --- 1. セキュリティ管理 (3問) ---
    {
        "no": 1,
        "major": "セキュリティ管理",
        "minor": "ポリシー管理",
        "question": "情報セキュリティポリシーの策定・承認・周知の手順と、年次見直しの実施状況を説明してください。",
    },
    {
        "no": 2,
        "major": "セキュリティ管理",
        "minor": "組織体制",
        "question": "情報セキュリティ管理責任者（CISO等）の設置状況と、組織横断的なセキュリティ推進体制を説明してください。",
    },
    {
        "no": 3,
        "major": "セキュリティ管理",
        "minor": "リスク管理",
        "question": "情報資産のリスクアセスメント手法と実施頻度、およびリスク対応計画の策定プロセスを説明してください。",
    },
    # --- 2. アクセス管理 (3問) ---
    {
        "no": 4,
        "major": "アクセス管理",
        "minor": "ユーザー認証",
        "question": "本番システムへのユーザー認証方式（多要素認証の導入状況を含む）と、認証失敗時のロックアウト設定を説明してください。",
    },
    {
        "no": 5,
        "major": "アクセス管理",
        "minor": "権限管理",
        "question": "業務システムにおけるアクセス権限の付与・変更・削除の承認フローと、定期的な棚卸しの実施状況を説明してください。",
    },
    {
        "no": 6,
        "major": "アクセス管理",
        "minor": "特権アカウント",
        "question": "特権ID（root・Administrator等）の管理方法と、利用時の承認・記録・モニタリングの仕組みを説明してください。",
    },
    # --- 3. ウイルス対策 (2問) ---
    {
        "no": 7,
        "major": "ウイルス対策",
        "minor": "マルウェア対策",
        "question": "サーバおよび端末におけるマルウェア対策ソフトの導入状況と、パターンファイルの更新頻度を説明してください。",
    },
    {
        "no": 8,
        "major": "ウイルス対策",
        "minor": "不正プログラム",
        "question": "未知のマルウェアや不正プログラムへの対策（EDR・サンドボックス等）の導入・運用状況を説明してください。",
    },
    # --- 4. ネットワーク管理 (3問) ---
    {
        "no": 9,
        "major": "ネットワーク管理",
        "minor": "境界防御",
        "question": "外部ネットワークとの境界におけるファイアウォール・WAF等の防御策と、ルール見直しの頻度を説明してください。",
    },
    {
        "no": 10,
        "major": "ネットワーク管理",
        "minor": "通信暗号化",
        "question": "顧客データを含む通信経路における暗号化方式（TLSバージョン等）と、証明書管理の運用手順を説明してください。",
    },
    {
        "no": 11,
        "major": "ネットワーク管理",
        "minor": "不正侵入検知",
        "question": "IDS/IPSの導入範囲とシグネチャ更新頻度、および検知時のアラート通知・対応フローを説明してください。",
    },
    # --- 5. バックアップ管理 (2問) ---
    {
        "no": 12,
        "major": "バックアップ管理",
        "minor": "バックアップ",
        "question": "重要データのバックアップ取得方式（フル・差分・増分）と取得頻度、遠隔地保管の実施状況を説明してください。",
    },
    {
        "no": 13,
        "major": "バックアップ管理",
        "minor": "復旧テスト",
        "question": "バックアップからのリストアテストの実施頻度と、目標復旧時間（RTO）・復旧時点（RPO）の設定状況を説明してください。",
    },
    # --- 6. インシデント対応 (3問) ---
    {
        "no": 14,
        "major": "インシデント対応",
        "minor": "対応手順",
        "question": "セキュリティインシデント発生時の初動対応手順（検知・封じ込め・根絶・復旧）の整備状況を説明してください。",
    },
    {
        "no": 15,
        "major": "インシデント対応",
        "minor": "報告体制",
        "question": "インシデント発生時の経営層・監督官庁・顧客への報告基準とエスカレーションフローを説明してください。",
    },
    {
        "no": 16,
        "major": "インシデント対応",
        "minor": "フォレンジック",
        "question": "デジタルフォレンジック調査の実施体制（社内・外部委託）と、証拠保全手順の整備状況を説明してください。",
    },
    # --- 7. 変更管理 (2問) ---
    {
        "no": 17,
        "major": "変更管理",
        "minor": "変更手順",
        "question": "本番環境に対する変更管理プロセス（申請・承認・テスト・リリース）と、緊急変更時の手順を説明してください。",
    },
    {
        "no": 18,
        "major": "変更管理",
        "minor": "脆弱性管理",
        "question": "OSやミドルウェアの脆弱性情報の収集体制と、セキュリティパッチ適用の優先度判断・適用手順を説明してください。",
    },
    # --- 8. 物理セキュリティ (2問) ---
    {
        "no": 19,
        "major": "物理セキュリティ",
        "minor": "入退室管理",
        "question": "データセンターおよびサーバルームへの入退室管理方式（生体認証・ICカード等）と入退記録の保管期間を説明してください。",
    },
    {
        "no": 20,
        "major": "物理セキュリティ",
        "minor": "設備管理",
        "question": "電源設備（UPS・自家発電）、空調設備、防火設備の冗長構成と定期点検の実施状況を説明してください。",
    },
    # --- 9. 教育・訓練 (2問) ---
    {
        "no": 21,
        "major": "教育・訓練",
        "minor": "セキュリティ教育",
        "question": "全従業員を対象とした情報セキュリティ教育の実施内容・頻度と、受講率の管理方法を説明してください。",
    },
    {
        "no": 22,
        "major": "教育・訓練",
        "minor": "標的型攻撃訓練",
        "question": "標的型攻撃メール訓練の実施頻度・対象範囲と、訓練結果に基づく改善施策の実施状況を説明してください。",
    },
    # --- 10. 外部委託管理 (3問) ---
    {
        "no": 23,
        "major": "外部委託管理",
        "minor": "委託先評価",
        "question": "外部委託先の選定時におけるセキュリティ評価基準と、定期的な委託先監査の実施状況を説明してください。",
    },
    {
        "no": 24,
        "major": "外部委託管理",
        "minor": "契約管理",
        "question": "外部委託契約における秘密保持条項・セキュリティ要件・損害賠償条項の規定状況を説明してください。",
    },
    {
        "no": 25,
        "major": "外部委託管理",
        "minor": "再委託管理",
        "question": "再委託の承認プロセスと、再委託先に対するセキュリティ管理基準の適用・監督体制を説明してください。",
    },
    # --- 11. システム開発 (3問) ---
    {
        "no": 26,
        "major": "システム開発",
        "minor": "開発プロセス",
        "question": "システム開発ライフサイクルにおけるセキュリティ要件定義とセキュリティレビューの実施工程を説明してください。",
    },
    {
        "no": 27,
        "major": "システム開発",
        "minor": "コード品質",
        "question": "ソースコードレビューおよび静的解析ツール（SAST）の導入状況と、指摘事項の是正管理手順を説明してください。",
    },
    {
        "no": 28,
        "major": "システム開発",
        "minor": "脆弱性テスト",
        "question": "リリース前の脆弱性診断（DAST・ペネトレーションテスト）の実施基準と、検出された脆弱性の対応方針を説明してください。",
    },
    # --- 12. ログ・監視 (2問) ---
    {
        "no": 29,
        "major": "ログ・監視",
        "minor": "ログ管理",
        "question": "重要システムの操作ログ・アクセスログの取得項目、保管期間、改ざん防止策を説明してください。",
    },
    {
        "no": 30,
        "major": "ログ・監視",
        "minor": "リアルタイム監視",
        "question": "SIEM等によるログの統合監視体制と、異常検知時のアラート基準・対応手順を説明してください。",
    },
]

NUM_QUESTIONS = len(QUESTIONS)

_MAJOR_TO_SOURCES: dict[str, list[str]] = {
    "セキュリティ管理": ["policies/security_policy.pdf", "past_answers/past_answer_2024.xlsx"],
    "アクセス管理": ["policies/access_control_policy.pdf", "policies/security_policy.pdf"],
    "ウイルス対策": ["policies/security_policy.pdf", "system_docs/operation_manual.pdf"],
    "ネットワーク管理": ["system_docs/infra_overview.pdf", "policies/encryption_standards.pdf"],
    "バックアップ管理": ["system_docs/dr_bcp_plan.pdf", "system_docs/infra_overview.pdf"],
    "インシデント対応": ["system_docs/incident_response.docx", "system_docs/operation_manual.pdf"],
    "変更管理": ["system_docs/operation_manual.pdf", "operations/change_management_log.xlsx"],
    "物理セキュリティ": ["system_docs/infra_overview.pdf", "policies/security_policy.pdf"],
    "教育・訓練": ["operations/security_training_record.docx", "system_docs/audit_compliance.docx"],
    "外部委託管理": ["regulations/outsourcing_management.pdf", "system_docs/audit_compliance.docx"],
    "システム開発": ["regulations/system_development_standards.docx", "policies/security_policy.pdf"],
    "ログ・監視": ["system_docs/operation_manual.pdf", "operations/vulnerability_assessment_2024.pdf"],
}
