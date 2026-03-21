import { useState, useEffect, useCallback, useRef } from "react"
import { useParams, Link } from "react-router-dom"
import { ArrowLeft, Upload, Trash2, Search, Plus, Pencil } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog"

type Bank = {
  id: number
  name: string
  code: string
  notes: string
}

type QaFile = {
  id: number
  bank_id: number
  qa_file_name: string
  file_format: string
  question_col: string
  answer_col: string
  header_row: number
  data_start_row: number
  table_index: number
}

type PastQA = {
  id: number
  bank_id: number
  question_text: string
  answer_text: string
  source_file: string
  created_at: string
}

const INITIAL_QF_FORM = {
  qa_file_name: "",
  file_format: "xlsx",
  question_col: "D",
  answer_col: "E",
  header_row: 1,
  data_start_row: 2,
  table_index: 0,
}

export default function BankDetailPage() {
  const { bankId } = useParams<{ bankId: string }>()
  const [bank, setBank] = useState<Bank | null>(null)
  const [qaFiles, setQaFiles] = useState<QaFile[]>([])
  const [pastQAs, setPastQAs] = useState<PastQA[]>([])
  const [search, setSearch] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  // QA file dialog state
  const [qfDialogOpen, setQfDialogOpen] = useState(false)
  const [editingQfId, setEditingQfId] = useState<number | null>(null)
  const [qfForm, setQfForm] = useState(INITIAL_QF_FORM)
  const [qfError, setQfError] = useState("")

  const loadBank = useCallback(async () => {
    const res = await apiFetch(`/api/banks/${bankId}`)
    if (res.ok) setBank(await res.json())
  }, [bankId])

  const loadQaFiles = useCallback(async () => {
    const res = await apiFetch(`/api/banks/${bankId}/qa-files`)
    if (res.ok) setQaFiles(await res.json())
  }, [bankId])

  const loadPastQAs = useCallback(async () => {
    const res = await apiFetch(`/api/banks/${bankId}/past-answers`)
    if (res.ok) setPastQAs(await res.json())
  }, [bankId])

  useEffect(() => {
    loadBank()
    loadQaFiles()
    loadPastQAs()
  }, [loadBank, loadQaFiles, loadPastQAs])

  const openCreateQf = () => {
    setEditingQfId(null)
    setQfForm(INITIAL_QF_FORM)
    setQfError("")
    setQfDialogOpen(true)
  }

  const openEditQf = (qf: QaFile) => {
    setEditingQfId(qf.id)
    setQfForm({
      qa_file_name: qf.qa_file_name,
      file_format: qf.file_format,
      question_col: qf.question_col,
      answer_col: qf.answer_col,
      header_row: qf.header_row,
      data_start_row: qf.data_start_row,
      table_index: qf.table_index,
    })
    setQfError("")
    setQfDialogOpen(true)
  }

  const handleSaveQf = async () => {
    setQfError("")
    const url = editingQfId
      ? `/api/banks/${bankId}/qa-files/${editingQfId}`
      : `/api/banks/${bankId}/qa-files`
    const method = editingQfId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(qfForm) })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      setQfError(data.detail || "保存に失敗しました")
      return
    }
    setQfDialogOpen(false)
    loadQaFiles()
  }

  const handleDeleteQf = async (qfId: number) => {
    if (!confirm("このQAファイルを削除しますか？")) return
    await apiFetch(`/api/banks/${bankId}/qa-files/${qfId}`, { method: "DELETE" })
    loadQaFiles()
  }

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

      <Card>
        <CardHeader className="pb-2">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm">QAファイル ({qaFiles.length}件)</CardTitle>
            <Button onClick={openCreateQf} size="sm" variant="outline">
              <Plus className="h-3 w-3 mr-1" />
              追加
            </Button>
          </div>
          <CardDescription>銀行名 + QAファイル名で一意。ファイルごとにフォーマット設定を管理します。</CardDescription>
        </CardHeader>
        <CardContent>
          {qaFiles.length === 0 ? (
            <p className="text-sm text-muted-foreground">QAファイルが登録されていません</p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>QAファイル名</TableHead>
                  <TableHead>形式</TableHead>
                  <TableHead>質問列</TableHead>
                  <TableHead>回答列</TableHead>
                  <TableHead>ヘッダー行</TableHead>
                  <TableHead>データ開始行</TableHead>
                  <TableHead className="w-20"></TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {qaFiles.map((qf) => (
                  <TableRow key={qf.id}>
                    <TableCell className="font-medium">{qf.qa_file_name}</TableCell>
                    <TableCell>{qf.file_format.toUpperCase()}</TableCell>
                    <TableCell>{qf.question_col}</TableCell>
                    <TableCell>{qf.answer_col}</TableCell>
                    <TableCell>{qf.header_row}</TableCell>
                    <TableCell>{qf.data_start_row}</TableCell>
                    <TableCell>
                      <div className="flex gap-1">
                        <Button variant="ghost" size="icon" onClick={() => openEditQf(qf)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" onClick={() => handleDeleteQf(qf.id)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
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

      <Dialog open={qfDialogOpen} onOpenChange={setQfDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingQfId ? "QAファイルを編集" : "QAファイルを追加"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {qfError && <p className="text-sm text-destructive">{qfError}</p>}
            <div className="space-y-1">
              <Label>QAファイル名</Label>
              <Input
                value={qfForm.qa_file_name}
                onChange={(e) => setQfForm({ ...qfForm, qa_file_name: e.target.value })}
                placeholder="セキュリティチェックシート"
              />
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>ファイル形式</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={qfForm.file_format}
                  onChange={(e) => setQfForm({ ...qfForm, file_format: e.target.value })}
                >
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="docx">Word (.docx)</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>質問列</Label>
                <Input value={qfForm.question_col} onChange={(e) => setQfForm({ ...qfForm, question_col: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>回答列</Label>
                <Input value={qfForm.answer_col} onChange={(e) => setQfForm({ ...qfForm, answer_col: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>ヘッダー行</Label>
                <Input type="number" value={qfForm.header_row} onChange={(e) => setQfForm({ ...qfForm, header_row: Number(e.target.value) })} />
              </div>
              <div className="space-y-1">
                <Label>データ開始行</Label>
                <Input type="number" value={qfForm.data_start_row} onChange={(e) => setQfForm({ ...qfForm, data_start_row: Number(e.target.value) })} />
              </div>
              {qfForm.file_format === "docx" && (
                <div className="space-y-1">
                  <Label>テーブル番号</Label>
                  <Input type="number" value={qfForm.table_index} onChange={(e) => setQfForm({ ...qfForm, table_index: Number(e.target.value) })} />
                </div>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setQfDialogOpen(false)}>キャンセル</Button>
            <Button onClick={handleSaveQf}>{editingQfId ? "更新" : "追加"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
