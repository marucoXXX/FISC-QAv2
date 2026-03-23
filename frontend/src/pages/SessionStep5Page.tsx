import { useState, useEffect, useCallback } from "react"
import { useParams } from "react-router-dom"
import { Download, Check } from "lucide-react"
import { apiFetch, getApiBaseUrl } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { StepIndicator } from "@/components/StepIndicator"

type SessionQuestion = {
  question_no: number
  question_text: string
  major: string
  minor: string
  answer_source: string
  answer_text: string
  source_references: string[]
  confidence: string
  add_to_common: number
  assessment_mark: string
  extra_columns?: string
  is_heading?: number
}

type ColumnDef = {
  col: string
  role: string
  description: string
}

type ExtraCol = {
  role: string
  description: string
  value: string
}

type Stats = {
  total: number
  past_match: number
  common_match: number
  generated: number
  manual: number
  pending: number
}

const ROLES_READ = new Set(["question", "category", "number", "reference", "remarks"])

const sourceLabels: Record<string, { label: string; color: string }> = {
  past_match: { label: "過去回答", color: "bg-blue-100 text-blue-700" },
  common_match: { label: "共通回答", color: "bg-purple-100 text-purple-700" },
  generated: { label: "AI生成", color: "bg-green-100 text-green-700" },
  manual: { label: "手動", color: "bg-yellow-100 text-yellow-700" },
  pending: { label: "未回答", color: "bg-gray-100 text-gray-500" },
}

function proposalMessage(q: SessionQuestion): string {
  if (!q.answer_text) {
    return "過去回答・共通回答・設計/運用ドキュメントからは回答が見つかりませんでした。手動での回答入力をお願いします。"
  }
  const refs = q.source_references.length > 0 ? q.source_references.join(", ") : ""
  switch (q.answer_source) {
    case "past_match": return "過去回答を参照してAIからの意見です。"
    case "common_match": return "共通回答DBを参照してAIからの意見です。"
    case "generated": return refs
      ? `設計/運用ドキュメント（${refs}）を参照してAIからの意見です。`
      : "設計/運用ドキュメントを参照してAIからの意見です。"
    case "manual": return "手動で入力された回答です。"
    default: return ""
  }
}

function parseColDefs(raw?: string): ColumnDef[] {
  if (!raw || raw === "[]") return []
  try { return JSON.parse(raw) } catch { return [] }
}

function parseExtraCols(raw?: string): Record<string, ExtraCol> {
  if (!raw || raw === "{}") return {}
  try { return JSON.parse(raw) } catch { return {} }
}

export default function SessionStep5Page() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [questions, setQuestions] = useState<SessionQuestion[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [accumulated, setAccumulated] = useState(false)
  const [drafts, setDrafts] = useState<Record<number, string>>({})
  const [savedDrafts, setSavedDrafts] = useState<Record<number, string>>({})
  const [saving, setSaving] = useState<Record<number, boolean>>({})
  const [colDefs, setColDefs] = useState<ColumnDef[]>([])

  const load = useCallback(async () => {
    const res = await apiFetch(`/api/sessions/${sessionId}/step5/summary`)
    if (res.ok) {
      const data = await res.json()
      setQuestions(data.questions)
      setStats(data.stats)
      setColDefs(parseColDefs(data.session?.column_definitions))
      const initDrafts: Record<number, string> = {}
      for (const q of data.questions as SessionQuestion[]) {
        const confident = q.answer_source !== "pending" && q.confidence !== "low"
        initDrafts[q.question_no] = confident ? q.answer_text : ""
      }
      setDrafts((prev) => {
        const next = { ...initDrafts }
        for (const [k, v] of Object.entries(prev)) {
          if (k in next) next[Number(k)] = v
        }
        return next
      })
      setSavedDrafts(initDrafts)
    }
  }, [sessionId])

  useEffect(() => { load() }, [load])

  const saveDraft = async (qno: number) => {
    setSaving((prev) => ({ ...prev, [qno]: true }))
    await apiFetch(`/api/sessions/${sessionId}/questions/${qno}`, {
      method: "PUT",
      body: JSON.stringify({ answer_text: drafts[qno] || "", add_to_common: false }),
    })
    setSavedDrafts((prev) => ({ ...prev, [qno]: drafts[qno] || "" }))
    setSaving((prev) => ({ ...prev, [qno]: false }))
  }

  const handleAccumulate = async () => {
    if (!confirm("回答を過去回答DBに蓄積しますか？次回以降のワークフローで再利用されます。")) return
    const res = await apiFetch(`/api/sessions/${sessionId}/step5/finalize`, { method: "PUT" })
    if (res.ok) {
      setAccumulated(true)
      load()
    }
  }

  const handleExport = () => {
    window.open(`${getApiBaseUrl()}/api/sessions/${sessionId}/export`, "_blank")
  }

  // Format-aware column groups
  const hasColDefs = colDefs.length > 0
  const questionCol = colDefs.find((d) => d.role === "question")
  const readCols = colDefs.filter((d) => ROLES_READ.has(d.role) && d.role !== "question")
  const writeCols = colDefs.filter((d) => d.role === "answer" || d.role === "judgment")

  return (
    <div className="space-y-4">
      <StepIndicator current={5} />

      {stats && (
        <div className="flex items-center gap-4 text-sm">
          <span>全{stats.total}件:</span>
          {stats.past_match > 0 && <span className="px-2 py-0.5 rounded bg-blue-100 text-blue-700">過去回答 {stats.past_match}</span>}
          {stats.common_match > 0 && <span className="px-2 py-0.5 rounded bg-purple-100 text-purple-700">共通回答 {stats.common_match}</span>}
          {stats.generated > 0 && <span className="px-2 py-0.5 rounded bg-green-100 text-green-700">AI生成 {stats.generated}</span>}
          {stats.manual > 0 && <span className="px-2 py-0.5 rounded bg-yellow-100 text-yellow-700">手動 {stats.manual}</span>}
          {stats.pending > 0 && <span className="px-2 py-0.5 rounded bg-gray-100 text-gray-500">未回答 {stats.pending}</span>}
        </div>
      )}

      <div className="flex items-center justify-end gap-2">
        {!accumulated ? (
          <Button variant="outline" onClick={handleAccumulate}>
            <Check className="h-4 w-4 mr-1" />
            過去回答DBに蓄積
          </Button>
        ) : (
          <span className="text-sm text-green-600 font-medium">蓄積済み</span>
        )}
        <Button onClick={handleExport}>
          <Download className="h-4 w-4 mr-1" />
          エクスポート
        </Button>
      </div>

      <div className="space-y-3">
        {questions.map((q) => {
          const src = sourceLabels[q.answer_source] || sourceLabels.pending
          const message = proposalMessage(q)
          const extras = parseExtraCols(q.extra_columns)

          // Heading row: show minimal card
          if (q.is_heading) {
            return (
              <Card key={q.question_no} className="py-2 gap-0 bg-muted/30">
                <CardHeader className="py-0">
                  <CardTitle className="flex items-center gap-2 text-sm text-muted-foreground">
                    <span className="font-mono">#{q.question_no}</span>
                    <span className="text-xs px-2 py-0.5 rounded bg-slate-100 text-slate-500">見出し行</span>
                    <span className="font-medium">{q.question_text}</span>
                  </CardTitle>
                </CardHeader>
              </Card>
            )
          }

          return (
            <Card key={q.question_no} className="py-4 gap-3">
              <CardHeader className="py-0">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-muted-foreground">#{q.question_no}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${src.color}`}>{src.label}</span>
                  {q.confidence && (
                    <span className={`text-xs px-2 py-0.5 rounded ${
                      q.confidence === "high" ? "bg-emerald-100 text-emerald-700" :
                      q.confidence === "medium" ? "bg-amber-100 text-amber-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      AI確信度: {q.confidence === "high" ? "高" : q.confidence === "medium" ? "中" : "低"}
                    </span>
                  )}
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-3 py-0">

                {hasColDefs ? (
                  <>
                    {/* Format-aware: question column */}
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">
                        {questionCol?.description || "質問"}
                      </p>
                      <p className="text-sm whitespace-pre-wrap">{q.question_text}</p>
                    </div>

                    {/* Format-aware: read columns */}
                    {readCols.map((cd) => {
                      const extra = extras[cd.col]
                      if (!extra?.value) return null
                      return (
                        <div key={cd.col}>
                          <p className="text-xs font-medium text-muted-foreground mb-1">{cd.description}</p>
                          <p className="text-sm whitespace-pre-wrap">{extra.value}</p>
                        </div>
                      )
                    })}

                    {/* Format-aware: write columns */}
                    {writeCols.map((cd, cdIdx) => {
                      // 複数answer列がある場合、判定結果に応じて活性/非活性を切替
                      const answerColsOnly = writeCols.filter((w) => w.role === "answer")
                      const hasMultipleAnswers = answerColsOnly.length >= 2
                      const isFirstAnswer = cd.role === "answer" && answerColsOnly[0]?.col === cd.col
                      const mark = q.assessment_mark || ""
                      const isActiveAnswer = !hasMultipleAnswers
                        || cd.role !== "answer"
                        || (isFirstAnswer && (mark === "○" || !mark))
                        || (!isFirstAnswer && (mark === "△" || mark === "×"))

                      return (
                      <div key={cd.col} className={`border-t pt-2 ${!isActiveAnswer ? "opacity-40" : ""}`}>
                        <p className="text-xs font-medium text-muted-foreground mb-1">
                          {cd.description}
                          {cd.role === "judgment" && <span className="text-[10px] ml-1">(判定)</span>}
                          {cd.role === "answer" && <span className="text-[10px] ml-1">(回答)</span>}
                        </p>
                        {cd.role === "judgment" ? (
                          <select
                            className="h-8 rounded border border-input bg-transparent px-2 text-sm"
                            value={q.assessment_mark || ""}
                            onChange={(e) => {
                              // TODO: save assessment_mark via API
                            }}
                          >
                            <option value="">未選択</option>
                            <option value="○">○</option>
                            <option value="△">△</option>
                            <option value="×">×</option>
                          </select>
                        ) : (
                          <div className="flex gap-2 items-start">
                            <textarea
                              className="flex-1 rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[60px] resize-y"
                              value={drafts[q.question_no] ?? ""}
                              onChange={(e) => setDrafts((prev) => ({ ...prev, [q.question_no]: e.target.value }))}
                              placeholder="回答を入力してください"
                            />
                            <SaveButton
                              isSaving={!!saving[q.question_no]}
                              isChanged={(drafts[q.question_no] ?? "") !== (savedDrafts[q.question_no] ?? "")}
                              onSave={() => saveDraft(q.question_no)}
                            />
                          </div>
                        )}
                      </div>
                      )
                    })}
                  </>
                ) : (
                  <>
                    {/* Legacy fallback */}
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">質問</p>
                      <p className="text-sm whitespace-pre-wrap">{q.question_text}</p>
                    </div>
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">回答案</p>
                      <div className="flex gap-2 items-start">
                        <textarea
                          className="flex-1 rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[60px] resize-y"
                          value={drafts[q.question_no] ?? ""}
                          onChange={(e) => setDrafts((prev) => ({ ...prev, [q.question_no]: e.target.value }))}
                          placeholder="回答を入力してください"
                        />
                        <SaveButton
                          isSaving={!!saving[q.question_no]}
                          isChanged={(drafts[q.question_no] ?? "") !== (savedDrafts[q.question_no] ?? "")}
                          onSave={() => saveDraft(q.question_no)}
                        />
                      </div>
                    </div>
                  </>
                )}

                {/* AI proposal */}
                <div className="border-t pt-3">
                  <p className="text-xs font-medium text-muted-foreground mb-1">AIからの提案</p>
                  <p className="text-xs text-muted-foreground mb-2 italic">{message}</p>
                  {q.answer_text ? (
                    <p className="text-sm whitespace-pre-wrap text-muted-foreground">{q.answer_text}</p>
                  ) : (
                    <p className="text-sm text-muted-foreground italic">提案なし</p>
                  )}
                </div>

              </CardContent>
            </Card>
          )
        })}
      </div>
    </div>
  )
}

function SaveButton({ isSaving, isChanged, onSave }: { isSaving: boolean; isChanged: boolean; onSave: () => void }) {
  if (isSaving) return <Button variant="outline" size="sm" className="shrink-0" disabled>保存中...</Button>
  if (!isChanged) return <Button variant="outline" size="sm" className="shrink-0 text-muted-foreground" disabled>保存済み</Button>
  return <Button variant="default" size="sm" className="shrink-0" onClick={onSave}>保存</Button>
}
