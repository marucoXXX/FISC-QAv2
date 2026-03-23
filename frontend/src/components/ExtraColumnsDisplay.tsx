/**
 * extra_columns の読み取り列情報を表示するコンポーネント。
 * session_questions の extra_columns JSON を受け取り、列名・値を表示する。
 */

const ROLE_LABELS: Record<string, string> = {
  category: "分類",
  number: "番号",
  reference: "参照情報",
  remarks: "備考",
  other: "その他",
}

type ExtraCol = {
  role: string
  description: string
  value: string
}

export function ExtraColumnsDisplay({ extraColumnsRaw }: { extraColumnsRaw?: string }) {
  if (!extraColumnsRaw || extraColumnsRaw === "{}") return null

  let extras: Record<string, ExtraCol>
  try {
    extras = JSON.parse(extraColumnsRaw)
  } catch {
    return null
  }

  const entries = Object.entries(extras).filter(([, v]) => v.value)
  if (entries.length === 0) return null

  return (
    <div className="space-y-1">
      {entries.map(([col, data]) => (
        <div key={col} className="flex gap-2 text-xs">
          <span className="text-muted-foreground shrink-0 min-w-[60px]">
            {data.description || ROLE_LABELS[data.role] || col}:
          </span>
          <span className="whitespace-pre-wrap">{data.value}</span>
        </div>
      ))}
    </div>
  )
}
