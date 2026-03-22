import { useState, useEffect, useCallback } from "react"
import { useParams } from "react-router-dom"
import { Download, Pencil, Check, RotateCcw } from "lucide-react"
import { apiFetch, getApiBaseUrl } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card"
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"
import { Label } from "@/components/ui/label"
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
}

type Stats = {
  total: number
  past_match: number
  common_match: number
  generated: number
  manual: number
  pending: number
}

const sourceLabels: Record<string, { label: string; color: string }> = {
  past_match: { label: "過去回答", color: "bg-blue-100 text-blue-700" },
  common_match: { label: "共通回答", color: "bg-purple-100 text-purple-700" },
  generated: { label: "AI生成", color: "bg-green-100 text-green-700" },
  manual: { label: "手動", color: "bg-yellow-100 text-yellow-700" },
  pending: { label: "未回答", color: "bg-gray-100 text-gray-500" },
}

export default function SessionStep5Page() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const [questions, setQuestions] = useState<SessionQuestion[]>([])
  const [stats, setStats] = useState<Stats | null>(null)
  const [editQ, setEditQ] = useState<SessionQuestion | null>(null)
  const [editText, setEditText] = useState("")
  const [addToCommon, setAddToCommon] = useState(false)
  const [finalized, setFinalized] = useState(false)

  const load = useCallback(async () => {
    const res = await apiFetch(`/api/sessions/${sessionId}/step5/summary`)
    if (res.ok) {
      const data = await res.json()
      setQuestions(data.questions)
      setStats(data.stats)
      setFinalized(data.session.status === "completed")
    }
  }, [sessionId])

  useEffect(() => { load() }, [load])

  const openEdit = (q: SessionQuestion) => {
    setEditQ(q)
    setEditText(q.answer_text)
    setAddToCommon(q.add_to_common === 1)
  }

  const saveEdit = async () => {
    if (!editQ) return
    await apiFetch(`/api/sessions/${sessionId}/questions/${editQ.question_no}`, {
      method: "PUT",
      body: JSON.stringify({ answer_text: editText, add_to_common: addToCommon }),
    })
    setEditQ(null)
    load()
  }

  const handleFinalize = async () => {
    if (!confirm("回答を確定しますか？過去回答DBに自動蓄積されます。")) return
    const res = await apiFetch(`/api/sessions/${sessionId}/step5/finalize`, { method: "PUT" })
    if (res.ok) {
      setFinalized(true)
      load()
    }
  }

  const handleExport = () => {
    window.open(`${getApiBaseUrl()}/api/sessions/${sessionId}/export`, "_blank")
  }

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
        {!finalized ? (
          <Button onClick={handleFinalize}>
            <Check className="h-4 w-4 mr-1" />
            確定して蓄積
          </Button>
        ) : (
          <span className="text-sm text-green-600 font-medium">確定済み</span>
        )}
        <Button variant="outline" onClick={handleExport}>
          <Download className="h-4 w-4 mr-1" />
          エクスポート
        </Button>
      </div>

      <div className="space-y-3">
        {questions.map((q) => {
          const src = sourceLabels[q.answer_source] || sourceLabels.pending
          return (
            <Card key={q.question_no} className="py-4 gap-3">
              <CardHeader className="py-0">
                <CardTitle className="flex items-center gap-2 text-sm">
                  <span className="font-mono text-muted-foreground">#{q.question_no}</span>
                  <span className={`text-xs px-2 py-0.5 rounded ${src.color}`}>
                    {src.label}
                  </span>
                  {q.assessment_mark && (
                    <span className={`text-xs font-bold px-2 py-0.5 rounded ${
                      q.assessment_mark === "\u25CB" ? "bg-green-100 text-green-700" :
                      q.assessment_mark === "\u25B3" ? "bg-yellow-100 text-yellow-700" :
                      "bg-red-100 text-red-700"
                    }`}>
                      {q.assessment_mark}
                    </span>
                  )}
                </CardTitle>
                <CardAction>
                  {!finalized && (
                    <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEdit(q)}>
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </CardAction>
              </CardHeader>
              <CardContent className="space-y-3 py-0">
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">質問</p>
                  <p className="text-sm whitespace-pre-wrap">{q.question_text}</p>
                </div>
                <div>
                  <p className="text-xs font-medium text-muted-foreground mb-1">回答</p>
                  <p className="text-sm whitespace-pre-wrap">
                    {q.answer_text || <span className="text-muted-foreground italic">未回答</span>}
                  </p>
                  {q.source_references.length > 0 && (
                    <p className="text-xs text-muted-foreground mt-1">
                      参照: {q.source_references.join(", ")}
                    </p>
                  )}
                </div>
              </CardContent>
            </Card>
          )
        })}
      </div>

      <Dialog open={!!editQ} onOpenChange={(open) => !open && setEditQ(null)}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>回答を編集 (Q{editQ?.question_no})</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="text-sm text-muted-foreground">{editQ?.question_text}</div>
            <div className="space-y-1">
              <Label>回答</Label>
              <textarea
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[120px]"
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={addToCommon}
                onChange={(e) => setAddToCommon(e.target.checked)}
                className="rounded"
              />
              共通回答DBに追加
            </label>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setEditQ(null)}>キャンセル</Button>
            <Button onClick={saveEdit}>保存</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
