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
}

const FORMAT_TYPE_LABELS: Record<string, string> = {
  choices: "選択肢＋備考型",
  assessment: "○/△/× 判定型",
  freetext: "自由記述型",
}

type Bank = {
  id: number
  name: string
  code: string
  notes: string
  past_qa_count: number
  qa_file_count: number
}

type Row = {
  bank: Bank
  qaFile: QaFile | null
}

const INITIAL_BANK_FORM = {
  name: "",
  code: "",
  notes: "",
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

export default function BankListPage() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [qaFilesMap, setQaFilesMap] = useState<Record<number, QaFile[]>>({})

  // Bank dialog
  const [bankDialogOpen, setBankDialogOpen] = useState(false)
  const [editingBankId, setEditingBankId] = useState<number | null>(null)
  const [bankForm, setBankForm] = useState(INITIAL_BANK_FORM)
  const [bankError, setBankError] = useState("")

  // QA file dialog
  const [qfDialogOpen, setQfDialogOpen] = useState(false)
  const [editingQf, setEditingQf] = useState<{ bankId: number; qfId: number | null } | null>(null)
  const [qfForm, setQfForm] = useState(INITIAL_QF_FORM)
  const [qfError, setQfError] = useState("")

  const loadBanks = useCallback(async () => {
    const res = await apiFetch("/api/banks")
    if (res.ok) {
      const data: Bank[] = await res.json()
      setBanks(data)
      const filesMap: Record<number, QaFile[]> = {}
      await Promise.all(data.map(async (b) => {
        try {
          const r = await apiFetch(`/api/banks/${b.id}/qa-files`)
          if (r.ok) filesMap[b.id] = await r.json()
        } catch { /* ignore */ }
      }))
      setQaFilesMap(filesMap)
    }
  }, [])

  useEffect(() => { loadBanks() }, [loadBanks])

  // Build flat rows: one per bank+qaFile combination
  const rows: Row[] = []
  for (const bank of banks) {
    const files = qaFilesMap[bank.id] || []
    if (files.length === 0) {
      rows.push({ bank, qaFile: null })
    } else {
      for (const qf of files) {
        rows.push({ bank, qaFile: qf })
      }
    }
  }

  // --- Bank handlers ---
  const openCreateBank = () => {
    setEditingBankId(null)
    setBankForm(INITIAL_BANK_FORM)
    setBankError("")
    setBankDialogOpen(true)
  }

  const openEditBank = (bank: Bank) => {
    setEditingBankId(bank.id)
    setBankForm({ name: bank.name, code: bank.code, notes: bank.notes })
    setBankError("")
    setBankDialogOpen(true)
  }

  const handleSaveBank = async () => {
    setBankError("")
    const url = editingBankId ? `/api/banks/${editingBankId}` : "/api/banks"
    const method = editingBankId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(bankForm) })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      setBankError(data.detail || "保存に失敗しました")
      return
    }
    setBankDialogOpen(false)
    loadBanks()
  }

  const handleDeleteRow = async (row: Row) => {
    if (row.qaFile) {
      if (!confirm(`「${row.bank.name} / ${row.qaFile.qa_file_name}」を削除しますか？`)) return
      await apiFetch(`/api/banks/${row.bank.id}/qa-files/${row.qaFile.id}`, { method: "DELETE" })
    } else {
      if (!confirm(`「${row.bank.name}」を削除しますか？関連データも全て削除されます。`)) return
      await apiFetch(`/api/banks/${row.bank.id}`, { method: "DELETE" })
    }
    loadBanks()
  }

  // --- QA file handlers ---
  const openEditRow = (row: Row) => {
    if (row.qaFile) {
      setEditingQf({ bankId: row.bank.id, qfId: row.qaFile.id })
      setQfForm({
        qa_file_name: row.qaFile.qa_file_name,
        file_format: row.qaFile.file_format,
        question_col: row.qaFile.question_col,
        answer_col: row.qaFile.answer_col,
        header_row: row.qaFile.header_row,
        data_start_row: row.qaFile.data_start_row,
        table_index: row.qaFile.table_index,
        format_type: row.qaFile.format_type,
        choices_col: row.qaFile.choices_col,
        remarks_col: row.qaFile.remarks_col,
      })
      setQfError("")
      setQfDialogOpen(true)
    } else {
      openEditBank(row.bank)
    }
  }

  const handleSaveQf = async () => {
    if (!editingQf) return
    setQfError("")
    const url = editingQf.qfId
      ? `/api/banks/${editingQf.bankId}/qa-files/${editingQf.qfId}`
      : `/api/banks/${editingQf.bankId}/qa-files`
    const method = editingQf.qfId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(qfForm) })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      setQfError(data.detail || "保存に失敗しました")
      return
    }
    setQfDialogOpen(false)
    loadBanks()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">銀行管理</h2>
        <Button onClick={openCreateBank} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          新規追加
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>銀行コード</TableHead>
            <TableHead>銀行名</TableHead>
            <TableHead>QAファイル</TableHead>
            <TableHead className="text-right">過去Q&A</TableHead>
            <TableHead className="w-12"></TableHead>
            <TableHead className="w-12"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                銀行が登録されていません
              </TableCell>
            </TableRow>
          )}
          {rows.map((row) => {
            const key = row.qaFile ? `qf-${row.qaFile.id}` : `bank-${row.bank.id}`
            return (
              <TableRow key={key}>
                <TableCell className="text-muted-foreground">{row.bank.code}</TableCell>
                <TableCell>
                  <Link to={`/banks/${row.bank.id}`} className="font-medium hover:underline flex items-center gap-1.5">
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                    {row.bank.name}
                  </Link>
                </TableCell>
                <TableCell>
                  {row.qaFile ? row.qaFile.qa_file_name : (
                    <span className="text-muted-foreground text-xs">-</span>
                  )}
                </TableCell>
                <TableCell className="text-right">{row.bank.past_qa_count}件</TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" onClick={() => openEditRow(row)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                </TableCell>
                <TableCell>
                  <Button variant="ghost" size="icon" onClick={() => handleDeleteRow(row)}>
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>

      {/* Bank dialog */}
      <Dialog open={bankDialogOpen} onOpenChange={setBankDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingBankId ? "銀行を編集" : "銀行を追加"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {bankError && <p className="text-sm text-destructive">{bankError}</p>}
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>銀行名</Label>
                <Input value={bankForm.name} onChange={(e) => setBankForm({ ...bankForm, name: e.target.value })} placeholder="みずほ銀行" />
              </div>
              <div className="space-y-1">
                <Label>コード</Label>
                <Input value={bankForm.code} onChange={(e) => setBankForm({ ...bankForm, code: e.target.value })} placeholder="mizuho" />
              </div>
            </div>
            <div className="space-y-1">
              <Label>メモ</Label>
              <Input value={bankForm.notes} onChange={(e) => setBankForm({ ...bankForm, notes: e.target.value })} />
            </div>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setBankDialogOpen(false)}>キャンセル</Button>
            <Button onClick={handleSaveBank}>{editingBankId ? "更新" : "追加"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* QA file dialog */}
      <Dialog open={qfDialogOpen} onOpenChange={setQfDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>{editingQf?.qfId ? "QAファイルを編集" : "QAファイルを追加"}</DialogTitle>
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
            <Button onClick={handleSaveQf}>{editingQf?.qfId ? "更新" : "追加"}</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  )
}
