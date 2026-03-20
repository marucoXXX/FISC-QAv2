import { useState, useEffect, useCallback } from "react"
import { Link } from "react-router-dom"
import { Plus, Pencil, Trash2, Building2 } from "lucide-react"
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
  file_format: string
  question_col: string
  answer_col: string
  header_row: number
  data_start_row: number
  table_index: number
  notes: string
  past_qa_count: number
}

const INITIAL_FORM = {
  name: "",
  code: "",
  file_format: "xlsx",
  question_col: "D",
  answer_col: "E",
  header_row: 1,
  data_start_row: 2,
  table_index: 0,
  notes: "",
}

export default function BankListPage() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(INITIAL_FORM)
  const [error, setError] = useState("")

  const loadBanks = useCallback(async () => {
    const res = await apiFetch("/api/banks")
    if (res.ok) setBanks(await res.json())
  }, [])

  useEffect(() => { loadBanks() }, [loadBanks])

  const openCreate = () => {
    setEditingId(null)
    setForm(INITIAL_FORM)
    setError("")
    setDialogOpen(true)
  }

  const openEdit = (bank: Bank) => {
    setEditingId(bank.id)
    setForm({
      name: bank.name,
      code: bank.code,
      file_format: bank.file_format,
      question_col: bank.question_col,
      answer_col: bank.answer_col,
      header_row: bank.header_row,
      data_start_row: bank.data_start_row,
      table_index: bank.table_index,
      notes: bank.notes,
    })
    setError("")
    setDialogOpen(true)
  }

  const handleSave = async () => {
    setError("")
    const url = editingId ? `/api/banks/${editingId}` : "/api/banks"
    const method = editingId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(form) })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      setError(data.detail || "保存に失敗しました")
      return
    }
    setDialogOpen(false)
    loadBanks()
  }

  const handleDelete = async (bankId: number) => {
    if (!confirm("この銀行を削除しますか？関連する過去回答も全て削除されます。")) return
    await apiFetch(`/api/banks/${bankId}`, { method: "DELETE" })
    loadBanks()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">銀行管理</h2>
        <Button onClick={openCreate} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          新規追加
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>銀行名</TableHead>
            <TableHead>コード</TableHead>
            <TableHead>形式</TableHead>
            <TableHead>質問列</TableHead>
            <TableHead>回答列</TableHead>
            <TableHead className="text-right">過去Q&A</TableHead>
            <TableHead className="w-24"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {banks.length === 0 && (
            <TableRow>
              <TableCell colSpan={7} className="text-center text-muted-foreground py-8">
                銀行が登録されていません
              </TableCell>
            </TableRow>
          )}
          {banks.map((bank) => (
            <TableRow key={bank.id}>
              <TableCell>
                <Link to={`/banks/${bank.id}`} className="font-medium hover:underline flex items-center gap-1.5">
                  <Building2 className="h-4 w-4 text-muted-foreground" />
                  {bank.name}
                </Link>
              </TableCell>
              <TableCell className="text-muted-foreground">{bank.code}</TableCell>
              <TableCell>{bank.file_format.toUpperCase()}</TableCell>
              <TableCell>{bank.question_col}</TableCell>
              <TableCell>{bank.answer_col}</TableCell>
              <TableCell className="text-right">{bank.past_qa_count}件</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" onClick={() => openEdit(bank)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(bank.id)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingId ? "銀行を編集" : "銀行を追加"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>銀行名</Label>
                <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="みずほ銀行" />
              </div>
              <div className="space-y-1">
                <Label>コード</Label>
                <Input value={form.code} onChange={(e) => setForm({ ...form, code: e.target.value })} placeholder="mizuho" />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>ファイル形式</Label>
                <select
                  className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                  value={form.file_format}
                  onChange={(e) => setForm({ ...form, file_format: e.target.value })}
                >
                  <option value="xlsx">Excel (.xlsx)</option>
                  <option value="docx">Word (.docx)</option>
                </select>
              </div>
              <div className="space-y-1">
                <Label>質問列</Label>
                <Input value={form.question_col} onChange={(e) => setForm({ ...form, question_col: e.target.value })} />
              </div>
              <div className="space-y-1">
                <Label>回答列</Label>
                <Input value={form.answer_col} onChange={(e) => setForm({ ...form, answer_col: e.target.value })} />
              </div>
            </div>
            <div className="grid grid-cols-3 gap-4">
              <div className="space-y-1">
                <Label>ヘッダー行</Label>
                <Input type="number" value={form.header_row} onChange={(e) => setForm({ ...form, header_row: Number(e.target.value) })} />
              </div>
              <div className="space-y-1">
                <Label>データ開始行</Label>
                <Input type="number" value={form.data_start_row} onChange={(e) => setForm({ ...form, data_start_row: Number(e.target.value) })} />
              </div>
              {form.file_format === "docx" && (
                <div className="space-y-1">
                  <Label>テーブル番号</Label>
                  <Input type="number" value={form.table_index} onChange={(e) => setForm({ ...form, table_index: Number(e.target.value) })} />
                </div>
              )}
            </div>
            <div className="space-y-1">
              <Label>メモ</Label>
              <Input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDialogOpen(false)}>キャンセル</Button>
            <Button onClick={handleSave}>{editingId ? "更新" : "追加"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
