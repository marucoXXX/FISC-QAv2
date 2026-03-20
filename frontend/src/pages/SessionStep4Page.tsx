import { useState, useEffect, useRef } from "react"
import { useParams, useNavigate } from "react-router-dom"
import { Loader2 } from "lucide-react"
import { apiFetch, getApiBaseUrl } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { StepIndicator } from "@/components/StepIndicator"

export default function SessionStep4Page() {
  const { sessionId } = useParams<{ sessionId: string }>()
  const navigate = useNavigate()
  const [status, setStatus] = useState<"idle" | "running" | "done" | "error" | "skipped">("idle")
  const [progress, setProgress] = useState<string[]>([])
  const [error, setError] = useState("")
  const logRef = useRef<HTMLDivElement>(null)

  const startGeneration = async () => {
    setStatus("running")
    setProgress([])
    setError("")

    const res = await apiFetch(`/api/sessions/${sessionId}/step4/generate`, {
      method: "POST",
    })
    const data = await res.json()

    if (!res.ok) {
      setStatus("error")
      setError(data.detail || "生成開始に失敗しました")
      return
    }

    if (data.skipped) {
      setStatus("skipped")
      return
    }

    // SSE for progress
    const jobId = data.job_id
    const evtSource = new EventSource(
      `${getApiBaseUrl()}/api/sessions/${sessionId}/step4/progress/${jobId}`
    )

    evtSource.addEventListener("progress", (e) => {
      setProgress((prev) => [...prev, e.data])
    })

    evtSource.addEventListener("done", () => {
      setStatus("done")
      evtSource.close()
    })

    evtSource.addEventListener("error", (e) => {
      if (e instanceof MessageEvent) {
        setError(e.data)
      }
      setStatus("error")
      evtSource.close()
    })

    evtSource.onerror = () => {
      evtSource.close()
    }
  }

  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight
    }
  }, [progress])

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <StepIndicator current={4} />

      {status === "idle" && (
        <div className="text-center py-8 space-y-4">
          <p className="text-muted-foreground">
            未解決の質問について設計書等からAIが回答を生成します
          </p>
          <Button onClick={startGeneration}>生成を開始</Button>
        </div>
      )}

      {status === "running" && (
        <div className="space-y-4">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 className="h-4 w-4 animate-spin" />
            生成中...
          </div>
          <div
            ref={logRef}
            className="bg-muted rounded-lg p-4 h-64 overflow-y-auto font-mono text-xs space-y-1"
          >
            {progress.map((msg, i) => (
              <p key={i}>{msg}</p>
            ))}
          </div>
        </div>
      )}

      {status === "done" && (
        <div className="text-center py-8 space-y-4">
          <p className="text-green-600 font-medium">生成完了</p>
          <Button onClick={() => navigate(`/sessions/${sessionId}/step5`)}>
            Step5: 最終確認へ
          </Button>
        </div>
      )}

      {status === "skipped" && (
        <div className="text-center py-8 space-y-4">
          <p className="text-muted-foreground">生成が必要な質問はありません</p>
          <Button onClick={() => navigate(`/sessions/${sessionId}/step5`)}>
            Step5: 最終確認へ
          </Button>
        </div>
      )}

      {status === "error" && (
        <div className="text-center py-8 space-y-4">
          <p className="text-destructive">{error || "エラーが発生しました"}</p>
          <div className="flex justify-center gap-2">
            <Button variant="outline" onClick={startGeneration}>再試行</Button>
            <Button onClick={() => navigate(`/sessions/${sessionId}/step5`)}>
              スキップしてStep5へ
            </Button>
          </div>
        </div>
      )}
    </div>
  )
}
