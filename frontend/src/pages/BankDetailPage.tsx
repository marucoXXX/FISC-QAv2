import { useState, useEffect, useCallback, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Upload, Trash2, Search } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type Bank = {
  id: number
  name: string
  code: string
  file_format: string
  question_col: string
  answer_col: string
  header_row: number
  data_start_row: number
  table_index: number
  notes: string
}

type PastQA = {
  id: number
  bank_id: number
  question_text: string
  answer_text: string
  source_file: string
  created_at: string
}

export default function BankDetailPage() {
  const { bankId } = useParams<{ bankId: string }>()
  const [bank, setBank] = useState<Bank | null>(null)
  const [pastQAs, setPastQAs] = useState<PastQA[]>([])
  const [search, setSearch] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  const loadBank = useCallback(async () => {
    const res = await apiFetch(`/api/banks/${bankId}`)
    if (res.ok) setBank(await res.json())
  }, [bankId])

  const loadPastQAs = useCallback(async () => {
    const res = await apiFetch(`/api/banks/${bankId}/past-answers`)
    if (res.ok) setPastQAs(await res.json())
  }, [bankId])

  useEffect(() => {
    loadBank()
    loadPastQAs()
  }, [loadBank, loadPastQAs])

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    setUploading(true)
    setUploadMsg("")
    const formData = new FormData()
    formData.append("file", file)

    const res = await apiFetch(`/api/banks/${bankId}/past-answers/upload`, {
      method: "POST",
      body: formData,
    })
    const data = await res.json()
    if (res.ok) {
      setUploadMsg(data.message)
      loadPastQAs()
    } else {
      setUploadMsg(data.detail || "アップロードに失敗しました")
    }
    setUploading(false)
    if (fileInputRef.current) fileInputRef.current.value = ""
  }

  const handleDelete = async (pastQaId: number) => {
    if (!confirm("このQ&Aペアを削除しますか？")) return
    await apiFetch(`/api/banks/${bankId}/past-answers/${pastQaId}`, { method: "DELETE" })
    loadPastQAs()
  }

  const filtered = pastQAs.filter((qa) =>
    !search ||
    qa.question_text.includes(search) ||
    qa.answer_text.includes(search)
  )

  if (!bank) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <Link to="/banks">
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <h2 className="text-lg font-semibold">{bank.name}</h2>
        <span className="text-sm text-muted-foreground">({bank.code})</span>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">フォーマット設定</CardTitle>
          </CardHeader>
          <CardContent className="text-sm space-y-1">
            <div className="flex justify-between">
              <span className="text-muted-foreground">ファイル形式</span>
              <span>{bank.file_format.toUpperCase()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">質問列 / 回答列</span>
              <span>{bank.question_col} / {bank.answer_col}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">ヘッダー行 / データ開始行</span>
              <span>{bank.header_row} / {bank.data_start_row}</span>
            </div>
            {bank.file_format === "docx" && (
              <div className="flex justify-between">
                <span className="text-muted-foreground">テーブル番号</span>
                <span>{bank.table_index}</span>
              </div>
            )}
            {bank.notes && (
              <div className="pt-1 border-t">
                <span className="text-muted-foreground">メモ:</span> {bank.notes}
              </div>
            )}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="pb-2">
            <CardTitle className="text-sm">過去回答アップロード</CardTitle>
            <CardDescription>
              フォーマット設定に基づいてQ&Aペアを自動抽出します
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-2">
              <input
                ref={fileInputRef}
                type="file"
                accept=".xlsx,.docx"
                onChange={handleUpload}
                className="hidden"
              />
              <Button
                variant="outline"
                size="sm"
                onClick={() => fileInputRef.current?.click()}
                disabled={uploading}
              >
                <Upload className="h-4 w-4 mr-1" />
                {uploading ? "アップロード中..." : "ファイルを選択"}
              </Button>
            </div>
            {uploadMsg && (
              <p className="text-sm mt-2 text-muted-foreground">{uploadMsg}</p>
            )}
          </CardContent>
        </Card>
      </div>

      <div className="space-y-2">
        <div className="flex items-center justify-between">
          <h3 className="font-medium">過去Q&Aペア ({filtered.length}件)</h3>
          <div className="relative w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="検索..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8"
            />
          </div>
        </div>

        <Table>
          <TableHeader>
            <TableRow>
              <TableHead className="w-12">#</TableHead>
              <TableHead>質問</TableHead>
              <TableHead>回答</TableHead>
              <TableHead className="w-32">ソース</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={5} className="text-center text-muted-foreground py-8">
                  過去Q&Aペアがありません
                </TableCell>
              </TableRow>
            )}
            {filtered.map((qa, i) => (
              <TableRow key={qa.id}>
                <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="max-w-xs truncate">{qa.question_text}</TableCell>
                <TableCell className="max-w-xs truncate">{qa.answer_text}</TableCell>
                <TableCell className="text-xs text-muted-foreground truncate">{qa.source_file}</TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(qa.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  )
}
