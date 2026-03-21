import { useState, useEffect, useCallback } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Check, X } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
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
  answer_source: string
}

export default function SessionStep2Page() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [questions, setQuestions] = useState<SessionQuestion[]>([])
  const [matching, setMatching] = useState(false)
  const [matched, setMatched] = useState(false)
  const [decisions, setDecisions] = useState<Record<number, boolean>>({})

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
    const res = await apiFetch(`/api/sessions/${sessionId}/step2/match`, { method: "POST" })
    if (res.ok) {
      setMatched(true)
      load()
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
