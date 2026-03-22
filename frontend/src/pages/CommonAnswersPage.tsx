import { useState, useEffect, useCallback } from "react"
import { Plus, Pencil, Trash2, Search } from "lucide-react"
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

type CommonAnswer = {
  id: number
  question_pattern: string
  answer_text: string
  category: string
  source: string
  created_at: string
  updated_at: string
}

const INITIAL_FORM = {
  question_pattern: "",
  answer_text: "",
  category: "",
  source: "",
}

export default function CommonAnswersPage() {
  const [items, setItems] = useState<CommonAnswer[]>([])
  const [search, setSearch] = useState("")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(INITIAL_FORM)

  const load = useCallback(async () => {
    const params = search ? `?search=${encodeURIComponent(search)}` : ""
    const res = await apiFetch(`/api/common-answers${params}`)
    if (res.ok) setItems(await res.json())
  }, [search])

  useEffect(() => { load() }, [load])

  const openCreate = () => {
    setEditingId(null)
    setForm(INITIAL_FORM)
    setDialogOpen(true)
  }

  const openEdit = (item: CommonAnswer) => {
    setEditingId(item.id)
    setForm({
      question_pattern: item.question_pattern,
      answer_text: item.answer_text,
      category: item.category,
      source: item.source,
    })
    setDialogOpen(true)
  }

  const handleSave = async () => {
    const url = editingId ? `/api/common-answers/${editingId}` : "/api/common-answers"
    const method = editingId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(form) })
    if (res.ok) {
      setDialogOpen(false)
      load()
    }
  }

  const handleDelete = async (id: number) => {
    if (!confirm("この共通回答を削除しますか？")) return
    await apiFetch(`/api/common-answers/${id}`, { method: "DELETE" })
    load()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">共通回答DB管理</h2>
        <div className="flex items-center gap-2">
          <div className="relative w-64">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="検索..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="pl-8"
            />
          </div>
          <Button onClick={openCreate} size="sm">
            <Plus className="h-4 w-4 mr-1" />
            新規追加
          </Button>
        </div>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-12">#</TableHead>
            <TableHead>質問パターン</TableHead>
            <TableHead>回答</TableHead>
            <TableHead className="w-28">カテゴリ</TableHead>
            <TableHead className="w-28">出典</TableHead>
            <TableHead className="w-20"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {items.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="text-center text-muted-foreground py-8">
                共通回答が登録されていません
              </TableCell>
            </TableRow>
          )}
          {items.map((item, i) => (
            <TableRow key={item.id}>
              <TableCell className="text-muted-foreground">{i + 1}</TableCell>
              <TableCell className="max-w-xs truncate">{item.question_pattern}</TableCell>
              <TableCell className="max-w-xs truncate">{item.answer_text}</TableCell>
              <TableCell className="text-xs">{item.category}</TableCell>
              <TableCell className="text-xs text-muted-foreground">{item.source}</TableCell>
              <TableCell>
                <div className="flex gap-1">
                  <Button variant="ghost" size="icon" onClick={() => openEdit(item)}>
                    <Pencil className="h-4 w-4" />
                  </Button>
                  <Button variant="ghost" size="icon" onClick={() => handleDelete(item.id)}>
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
            <DialogTitle>{editingId ? "共通回答を編集" : "共通回答を追加"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div className="space-y-1">
              <Label>質問パターン</Label>
              <textarea
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[80px]"
                value={form.question_pattern}
                onChange={(e) => setForm({ ...form, question_pattern: e.target.value })}
                placeholder="セキュリティポリシーは策定されていますか？"
              />
            </div>
            <div className="space-y-1">
              <Label>回答</Label>
              <textarea
                className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[80px]"
                value={form.answer_text}
                onChange={(e) => setForm({ ...form, answer_text: e.target.value })}
                placeholder="当社ではセキュリティポリシーを策定しており..."
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-1">
                <Label>カテゴリ</Label>
                <Input
                  value={form.category}
                  onChange={(e) => setForm({ ...form, category: e.target.value })}
                  placeholder="セキュリティ管理"
                />
              </div>
              <div className="space-y-1">
                <Label>出典</Label>
                <Input
                  value={form.source}
                  onChange={(e) => setForm({ ...form, source: e.target.value })}
                  placeholder="security_policy.pdf"
                />
              </div>
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
