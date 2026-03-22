import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Check, X } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { diffWords } from "@/lib/textDiff"
import { Button } from "@/components/ui/button"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { StepIndicator } from "@/components/StepIndicator"

type SessionQuestion = {
  question_no: number
  question_text: string
  major: string
  minor: string
  past_question_text: string
  past_answer_text: string
  matched_past_qa_id: number | null
  match_judgment: string
  match_reason: string
  answer_source: string
}

export default function SessionStep2Page() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<SessionQuestion[]>([])
  const [matching, setMatching] = useState(false)
  const [matched, setMatched] = useState(false)
  const [decisions, setDecisions] = useState<Record<number, boolean>>({})
  const [strategy, setStrategy] = useState("cosine")
  const [error, setError] = useState("")

  const load = useCallback(async () => {
    const res = await apiFetch(`/api/sessions/${sessionId}/step2/results`)
    if (res.ok) {
      const data = await res.json()
      setQuestions(data)
      // Check if already matched
      if (data.some((q: SessionQuestion) => q.matched_past_qa_id)) {
        setMatched(true)
      }
    }
  }, [sessionId])

  useEffect(() => { load() }, [load])

  const runMatch = async () => {
    setMatching(true)
    setError("")
    const res = await apiFetch(`/api/sessions/${sessionId}/step2/match?match_strategy=${strategy}`, { method: "POST" })
    if (res.ok) {
      setMatched(true)
      load()
    } else {
      const msg = await res.text().catch(() => "")
      setError(`マッチングに失敗しました (${res.status})${msg ? `: ${msg}` : ""}`)
    }
    setMatching(false)
  }

  const toggleDecision = (qno: number, value: boolean) => {
    setDecisions((prev) => ({ ...prev, [qno]: value }))
  }

  const handleConfirm = async () => {
    const items = questions.map((q) => ({
      question_no: q.question_no,
      confirmed: decisions[q.question_no] ?? (q.matched_past_qa_id != null),
    }))
    const res = await apiFetch(`/api/sessions/${sessionId}/step2/confirm`, {
      method: "PUT",
      body: JSON.stringify(items),
    })
    if (res.ok) {
      navigate(`/sessions/${sessionId}/step3`)
    }
  }

  return (
    <div className="space-y-4">
      <StepIndicator current={2} />

      {!matched ? (
        <div className="text-center py-8 space-y-4">
          <p className="text-muted-foreground">過去回答とのマッチングを実行します</p>
          <div className="flex items-center justify-center gap-2">
            <label className="text-sm text-muted-foreground">戦略:</label>
            <select
              className="rounded-md border border-input bg-transparent px-2 py-1 text-sm"
              value={strategy}
              onChange={(e) => setStrategy(e.target.value)}
            >
              <option value="cosine">コサイン類似度</option>
              <option value="llm">LLM判定</option>
              <option value="hybrid">ハイブリッド</option>
            </select>
          </div>
          {error && <p className="text-sm text-destructive">{error}</p>}
          <Button onClick={runMatch} disabled={matching}>
            {matching ? "マッチング中..." : "マッチング実行"}
          </Button>
        </div>
      ) : (
        <>
          <div className="flex items-center justify-between">
            <p className="text-sm text-muted-foreground">
              {questions.filter((q) => q.matched_past_qa_id).length} / {questions.length} 件がマッチ
            </p>
            <Button onClick={handleConfirm}>確定してStep3へ</Button>
          </div>

          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-12">#</TableHead>
                <TableHead>今回の質問</TableHead>
                <TableHead>前回の質問</TableHead>
                <TableHead>
                  <div>差分</div>
                  <div className="flex items-center gap-2 mt-1 font-normal">
                    <span className="bg-red-100 text-red-800 line-through dark:bg-red-900/40 dark:text-red-300 text-xs px-1 rounded">前回のみ</span>
                    <span className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 text-xs px-1 rounded">今回のみ</span>
                  </div>
                </TableHead>
                <TableHead>LLM判定</TableHead>
                <TableHead>前回の回答</TableHead>
                <TableHead className="w-24 text-center">採用</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {questions.map((q) => {
                const hasMatch = !!q.matched_past_qa_id
                const isAccepted = decisions[q.question_no] ?? hasMatch
                return (
                  <TableRow key={q.question_no} className={!hasMatch ? "opacity-50" : ""}>
                    <TableCell className="font-mono text-xs">{q.question_no}</TableCell>
                    <TableCell className="text-sm">
                      <div className="whitespace-pre-wrap">{q.question_text}</div>
                    </TableCell>
                    <TableCell className="text-sm">
                      {hasMatch ? (
                        <div className="whitespace-pre-wrap">{q.past_question_text}</div>
                      ) : (
                        <span className="text-muted-foreground italic">過去回答なし</span>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {hasMatch && (() => {
                        const segments = diffWords(q.past_question_text, q.question_text)
                        const hasDiff = segments.some((s) => s.type !== "same")
                        if (!hasDiff) {
                          return <span className="text-muted-foreground">差分なし ✅</span>
                        }
                        return (
                          <div className="whitespace-pre-wrap">
                            {segments.map((seg, i) =>
                              seg.type === "same" ? (
                                <span key={i}>{seg.text}</span>
                              ) : seg.type === "added" ? (
                                <span key={i} className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300">{seg.text}</span>
                              ) : (
                                <span key={i} className="bg-red-100 text-red-800 line-through dark:bg-red-900/40 dark:text-red-300">{seg.text}</span>
                              )
                            )}
                          </div>
                        )
                      })()}
                    </TableCell>
                    <TableCell className="text-sm">
                      {hasMatch && q.match_judgment && (
                        <div className="space-y-1">
                          <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${
                            q.match_judgment === "reusable"
                              ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                              : q.match_judgment === "caution"
                              ? "bg-yellow-100 text-yellow-800 dark:bg-yellow-900/40 dark:text-yellow-300"
                              : "bg-red-100 text-red-800 dark:bg-red-900/40 dark:text-red-300"
                          }`}>
                            {q.match_judgment === "reusable" ? "✅ 同趣旨" :
                             q.match_judgment === "caution" ? "⚠️ 要注意" : "❌ 別趣旨"}
                          </span>
                          {q.match_reason && (
                            <p className="text-xs text-muted-foreground">{q.match_reason}</p>
                          )}
                        </div>
                      )}
                    </TableCell>
                    <TableCell className="text-sm">
                      {hasMatch && <div className="whitespace-pre-wrap">{q.past_answer_text}</div>}
                    </TableCell>
                    <TableCell className="text-center">
                      {hasMatch && (
                        <div className="flex justify-center gap-1">
                          <Button
                            variant={isAccepted ? "default" : "outline"}
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => toggleDecision(q.question_no, true)}
                          >
                            <Check className="h-3.5 w-3.5" />
                          </Button>
                          <Button
                            variant={!isAccepted ? "destructive" : "outline"}
                            size="icon"
                            className="h-7 w-7"
                            onClick={() => toggleDecision(q.question_no, false)}
                          >
                            <X className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      )}
                    </TableCell>
                  </TableRow>
                )
              })}
            </TableBody>
          </Table>
        </>
      )}
    </div>
  )
}
