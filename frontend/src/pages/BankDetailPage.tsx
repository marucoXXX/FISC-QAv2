import { useState, useEffect, useCallback, useRef } from "react"
import { useParams, Link, useNavigate } from "react-router-dom"
import { ArrowLeft, Upload, Trash2, Search, Plus, Pencil, ChevronDown, ChevronRight } from "lucide-react"
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

type ColumnDef = {
  col: string
  role: string
  description: string
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
  format_type: string
  choices_col: string
  remarks_col: string
  column_definitions?: string
  row_structure?: string
}

const ROLE_LABELS: Record<string, string> = {
  question: "質問",
  answer: "回答",
  category: "分類",
  number: "番号",
  reference: "参照",
  remarks: "備考",
  judgment: "判定",
  other: "他",
}

function parseColumnDefs(qf: QaFile): ColumnDef[] {
  if (!qf.column_definitions || qf.column_definitions === "[]") return []
  try {
    return JSON.parse(qf.column_definitions)
  } catch {
    return []
  }
}

type PastQA = {
  id: number
  bank_id: number
  question_text: string
  answer_text: string
  choices_text: string
  remarks_text: string
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
  format_type: "freetext",
  choices_col: "",
  remarks_col: "",
}

export default function BankDetailPage() {
  const { bankId } = useParams<{ bankId: string }>()
  const navigate = useNavigate()
  const [bank, setBank] = useState<Bank | null>(null)
  const [qaFiles, setQaFiles] = useState<QaFile[]>([])
  const [pastQAs, setPastQAs] = useState<PastQA[]>([])
  const [search, setSearch] = useState("")
  const [uploading, setUploading] = useState(false)
  const [uploadMsg, setUploadMsg] = useState("")
  const fileInputRef = useRef<HTMLInputElement>(null)

  // QA file dialog state
  const [qfDialogOpen, setQfDialogOpen] = useState(false)
  const [expandedQfId, setExpandedQfId] = useState<number | null>(null)
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
      format_type: qf.format_type,
      choices_col: qf.choices_col,
      remarks_col: qf.remarks_col,
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
            <div className="flex items-center gap-2">
              <Button onClick={() => navigate(`/banks/${bankId}/format-setup`)} size="sm" variant="outline">
                <Plus className="h-3 w-3 mr-1" />
                追加
              </Button>
              <button
                onClick={openCreateQf}
                className="text-xs text-muted-foreground hover:text-foreground underline"
              >
                手動で追加
              </button>
            </div>
          </div>
          <CardDescription>銀行名 + QAファイル名で一意。ファイルごとにフォーマット設定を管理します。</CardDescription>
        </CardHeader>
        <CardContent>
          {qaFiles.length === 0 ? (
            <p className="text-sm text-muted-foreground">QAファイルが登録されていません</p>
          ) : (
            <div className="space-y-2">
              {qaFiles.map((qf) => {
                const isExpanded = expandedQfId === qf.id
                const colDefs = parseColumnDefs(qf)
                return (
                  <div key={qf.id} className="border rounded-md">
                    {/* Summary row */}
                    <div
                      className="flex items-center gap-3 px-3 py-2 cursor-pointer hover:bg-muted/50"
                      onClick={() => setExpandedQfId(isExpanded ? null : qf.id)}
                    >
                      {isExpanded
                        ? <ChevronDown className="h-4 w-4 text-muted-foreground shrink-0" />
                        : <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0" />}
                      <span className="font-medium text-sm flex-1">{qf.qa_file_name}</span>
                      <span className="text-xs text-muted-foreground">{qf.file_format.toUpperCase()} / ヘッダー:{qf.header_row}行 / データ開始:{qf.data_start_row}行</span>
                      <div className="flex gap-1 shrink-0" onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => openEditQf(qf)}>
                          <Pencil className="h-3 w-3" />
                        </Button>
                        <Button variant="ghost" size="icon" className="h-7 w-7" onClick={() => handleDeleteQf(qf.id)}>
                          <Trash2 className="h-3 w-3" />
                        </Button>
                      </div>
                    </div>
                    {/* Expanded detail */}
                    {isExpanded && (
                      <div className="px-3 pb-3 pt-1 border-t space-y-3">
                        {colDefs.length > 0 ? (
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1">列定義</p>
                            <table className="w-full text-xs border-collapse">
                              <thead>
                                <tr className="border-b">
                                  <th className="text-left py-1 pr-3 font-medium text-muted-foreground w-16">列</th>
                                  <th className="text-left py-1 pr-3 font-medium text-muted-foreground w-32">役割</th>
                                  <th className="text-left py-1 font-medium text-muted-foreground">説明</th>
                                </tr>
                              </thead>
                              <tbody>
                                {colDefs.map((d, i) => (
                                  <tr key={i} className="border-b last:border-0">
                                    <td className="py-1 pr-3 font-mono">{d.col}</td>
                                    <td className="py-1 pr-3">
                                      <span className={`inline-block px-1.5 py-0.5 rounded text-[10px] ${
                                        ["question","category","number","reference","remarks"].includes(d.role)
                                          ? "bg-green-100 text-green-800"
                                          : ["answer","judgment"].includes(d.role)
                                            ? "bg-orange-100 text-orange-800"
                                            : "bg-neutral-100 text-neutral-700"
                                      }`}>
                                        {ROLE_LABELS[d.role] || d.role}
                                      </span>
                                    </td>
                                    <td className="py-1">{d.description}</td>
                                  </tr>
                                ))}
                              </tbody>
                            </table>
                          </div>
                        ) : (
                          <p className="text-xs text-muted-foreground">
                            列定義: 質問列={qf.question_col}, 回答列={qf.answer_col}
                            {qf.choices_col ? `, 判定列=${qf.choices_col}` : ""}
                            {qf.remarks_col ? `, 備考列=${qf.remarks_col}` : ""}
                          </p>
                        )}
                        {qf.row_structure && (
                          <div>
                            <p className="text-xs font-medium text-muted-foreground mb-1">行構造の説明</p>
                            <p className="text-xs whitespace-pre-wrap bg-muted/50 rounded p-2">{qf.row_structure}</p>
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                )
              })}
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
              <TableHead>選択肢/判定</TableHead>
              <TableHead>回答</TableHead>
              <TableHead>備考</TableHead>
              <TableHead className="w-32">ソース</TableHead>
              <TableHead className="w-12"></TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {filtered.length === 0 && (
              <TableRow>
                <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                  過去Q&Aペアがありません
                </TableCell>
              </TableRow>
            )}
            {filtered.map((qa, i) => (
              <TableRow key={qa.id}>
                <TableCell className="text-muted-foreground">{i + 1}</TableCell>
                <TableCell className="text-sm whitespace-pre-wrap">{qa.question_text}</TableCell>
                <TableCell className="text-sm whitespace-pre-wrap text-muted-foreground">{qa.choices_text || "-"}</TableCell>
                <TableCell className="text-sm whitespace-pre-wrap">{qa.answer_text}</TableCell>
                <TableCell className="text-sm whitespace-pre-wrap text-muted-foreground">{qa.remarks_text || "-"}</TableCell>
                <TableCell className="text-xs text-muted-foreground whitespace-pre-wrap">{qa.source_file}</TableCell>
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
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>QAファイル名</Label>
                <Input
                  value={qfForm.qa_file_name}
                  onChange={(e) => setQfForm({ ...qfForm, qa_file_name: e.target.value })}
                  placeholder="セキュリティチェックシート"
                />
              </div>
              <div className="space-y-1">
                <Label>フォーマット類型</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={qfForm.format_type}
                  onChange={(e) => setQfForm({ ...qfForm, format_type: e.target.value })}
                >
                  <option value="freetext">自由記述型</option>
                  <option value="choices">選択肢＋備考型</option>
                  <option value="assessment">○/△/× 判定型</option>
                </select>
              </div>
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
            {qfForm.format_type !== "freetext" && (
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1">
                  <Label>{qfForm.format_type === "choices" ? "選択肢列" : "判定欄列"}</Label>
                  <Input value={qfForm.choices_col} onChange={(e) => setQfForm({ ...qfForm, choices_col: e.target.value })} placeholder="F" />
                </div>
                <div className="space-y-1">
                  <Label>備考列</Label>
                  <Input value={qfForm.remarks_col} onChange={(e) => setQfForm({ ...qfForm, remarks_col: e.target.value })} placeholder="H" />
                </div>
              </div>
            )}
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
