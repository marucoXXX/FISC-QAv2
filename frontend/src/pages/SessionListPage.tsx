import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { Plus, FileText } from "lucide-react"
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

type Session = {
  id: number
  bank_name: string
  name: string
  current_step: number
  status: string
  created_at: string
}

const stepLabels: Record<number, string> = {
  1: "質問票アップロード",
  2: "過去回答マッチング",
  3: "共通回答マッチング",
  4: "AI回答生成",
  5: "最終確認",
}

export default function SessionListPage() {
  const [sessions, setSessions] = useState<Session[]>([])

  const load = useCallback(async () => {
    const res = await apiFetch("/api/sessions")
    if (res.ok) setSessions(await res.json())
  }, [])

  useEffect(() => { load() }, [load])

  const getStepUrl = (s: Session) => {
    if (s.status === "completed") return `/sessions/${s.id}/step5`
    return `/sessions/${s.id}/step${s.current_step}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">セッション</h2>
        <Link to="/sessions/new">
          <Button size="sm">
            <Plus className="h-4 w-4 mr-1" />
            新規セッション
          </Button>
        </Link>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>銀行</TableHead>
            <TableHead>質問票</TableHead>
            <TableHead>ステップ</TableHead>
            <TableHead>ステータス</TableHead>
            <TableHead>作成日</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {sessions.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                セッションがありません
              </TableCell>
            </TableRow>
          )}
          {sessions.map((s) => (
            <TableRow key={s.id}>
              <TableCell className="text-muted-foreground">{s.id}</TableCell>
              <TableCell>{s.bank_name}</TableCell>
              <TableCell>
                <Link to={getStepUrl(s)} className="flex items-center gap-1.5 hover:underline">
                  <FileText className="h-4 w-4 text-muted-foreground" />
                  {s.name}
                </Link>
              </TableCell>
              <TableCell>
                <span className="text-xs px-2 py-0.5 rounded-full bg-muted">
                  Step{s.current_step}: {stepLabels[s.current_step]}
                </span>
              </TableCell>
              <TableCell>
                <span className={`text-xs ${s.status === "completed" ? "text-green-600" : "text-yellow-600"}`}>
                  {s.status === "completed" ? "完了" : "進行中"}
                </span>
              </TableCell>
              <TableCell className="text-xs text-muted-foreground">
                {new Date(s.created_at).toLocaleDateString("ja-JP")}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
