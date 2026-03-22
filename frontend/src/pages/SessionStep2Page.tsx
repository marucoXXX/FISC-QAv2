import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Check, X } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { diffWords } from "@/lib/textDiff"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle, CardAction } from "@/components/ui/card"
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

          <div className="flex items-center gap-4 text-xs text-muted-foreground">
            <span>差分の凡例:</span>
            <span className="bg-red-100 text-red-800 line-through dark:bg-red-900/40 dark:text-red-300 px-1 rounded">前回のみ</span>
            <span className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300 px-1 rounded">今回のみ</span>
          </div>

          <div className="space-y-3">
            {questions.map((q) => {
              const hasMatch = !!q.matched_past_qa_id
              const isAccepted = decisions[q.question_no] ?? hasMatch
              return (
                <Card key={q.question_no} className={`py-4 gap-3 ${!hasMatch ? "opacity-50" : ""}`}>
                  <CardHeader className="py-0">
                    <CardTitle className="flex items-center gap-2 text-sm">
                      <span className="font-mono text-muted-foreground">#{q.question_no}</span>
                      {hasMatch ? (
                        <span className="text-xs px-2 py-0.5 rounded bg-blue-100 text-blue-700">マッチあり</span>
                      ) : (
                        <span className="text-xs px-2 py-0.5 rounded bg-gray-100 text-gray-500">過去回答なし</span>
                      )}
                      {hasMatch && q.match_judgment && (
                        <span className={`text-xs px-2 py-0.5 rounded-full ${
                          q.match_judgment === "reusable"
                            ? "bg-green-100 text-green-800"
                            : q.match_judgment === "caution"
                            ? "bg-yellow-100 text-yellow-800"
                            : "bg-red-100 text-red-800"
                        }`}>
                          {q.match_judgment === "reusable" ? "同趣旨" :
                           q.match_judgment === "caution" ? "要注意" : "別趣旨"}
                        </span>
                      )}
                      {hasMatch && q.match_reason && (
                        <span className="text-xs text-muted-foreground">{q.match_reason}</span>
                      )}
                    </CardTitle>
                    <CardAction>
                      {hasMatch && (
                        <div className="flex items-center gap-1">
                          <Button
                            variant={isAccepted ? "default" : "outline"}
                            size="sm"
                            className="h-7 text-xs px-2"
                            onClick={() => toggleDecision(q.question_no, true)}
                          >
                            <Check className="h-3.5 w-3.5 mr-1" />
                            採用
                          </Button>
                          <Button
                            variant={!isAccepted ? "destructive" : "outline"}
                            size="sm"
                            className="h-7 text-xs px-2"
                            onClick={() => toggleDecision(q.question_no, false)}
                          >
                            <X className="h-3.5 w-3.5 mr-1" />
                            不採用
                          </Button>
                        </div>
                      )}
                    </CardAction>
                  </CardHeader>
                  <CardContent className="space-y-3 py-0">
                    <div>
                      <p className="text-xs font-medium text-muted-foreground mb-1">今回の質問</p>
                      <p className="text-sm whitespace-pre-wrap">{q.question_text}</p>
                    </div>
                    {hasMatch && (
                      <>
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-1">前回の質問</p>
                          <p className="text-sm whitespace-pre-wrap">{q.past_question_text}</p>
                        </div>
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-1">差分</p>
                          {(() => {
                            const segments = diffWords(q.past_question_text, q.question_text)
                            const hasDiff = segments.some((s) => s.type !== "same")
                            if (!hasDiff) {
                              return <span className="text-sm text-muted-foreground">差分なし</span>
                            }
                            return (
                              <p className="text-sm whitespace-pre-wrap">
                                {segments.map((seg, i) =>
                                  seg.type === "same" ? (
                                    <span key={i}>{seg.text}</span>
                                  ) : seg.type === "added" ? (
                                    <span key={i} className="bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300">{seg.text}</span>
                                  ) : (
                                    <span key={i} className="bg-red-100 text-red-800 line-through dark:bg-red-900/40 dark:text-red-300">{seg.text}</span>
                                  )
                                )}
                              </p>
                            )
                          })()}
                        </div>
                        <div>
                          <p className="text-xs font-medium text-muted-foreground mb-1">前回の回答</p>
                          <p className="text-sm whitespace-pre-wrap">{q.past_answer_text}</p>
                        </div>
                      </>
                    )}
                  </CardContent>
                </Card>
              )
            })}
          </div>
        </>
      )}
    </div>
  )
}
