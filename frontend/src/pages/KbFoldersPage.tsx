import { useState, useEffect, useCallback } from "react"
import { Plus, Pencil, Trash2, FolderOpen } from "lucide-react"
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

type KbFolder = {
  id: number
  path: string
  label: string
  created_at: string
  updated_at: string
}

const INITIAL_FORM = { path: "", label: "" }

export default function KbFoldersPage() {
  const [folders, setFolders] = useState<KbFolder[]>([])
  const [dialogOpen, setDialogOpen] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [form, setForm] = useState(INITIAL_FORM)
  const [error, setError] = useState("")

  const loadFolders = useCallback(async () => {
    const res = await apiFetch("/api/kb-folders")
    if (res.ok) setFolders(await res.json())
  }, [])

  useEffect(() => { loadFolders() }, [loadFolders])

  const openCreate = () => {
    setEditingId(null)
    setForm(INITIAL_FORM)
    setError("")
    setDialogOpen(true)
  }

  const openEdit = (folder: KbFolder) => {
    setEditingId(folder.id)
    setForm({ path: folder.path, label: folder.label })
    setError("")
    setDialogOpen(true)
  }

  const handleSave = async () => {
    setError("")
    if (!form.path.trim()) {
      setError("パスを入力してください")
      return
    }
    const url = editingId ? `/api/kb-folders/${editingId}` : "/api/kb-folders"
    const method = editingId ? "PUT" : "POST"
    const res = await apiFetch(url, { method, body: JSON.stringify(form) })
    if (!res.ok) {
      const data = await res.json().catch(() => ({}))
      setError(data.detail || "保存に失敗しました")
      return
    }
    setDialogOpen(false)
    loadFolders()
  }

  const handleDelete = async (folder: KbFolder) => {
    const label = folder.label || folder.path
    if (!confirm(`「${label}」を削除しますか？`)) return
    await apiFetch(`/api/kb-folders/${folder.id}`, { method: "DELETE" })
    loadFolders()
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">KBフォルダ管理</h2>
        <Button onClick={openCreate} size="sm">
          <Plus className="h-4 w-4 mr-1" />
          新規追加
        </Button>
      </div>

      <Table>
        <TableHeader>
          <TableRow>
            <TableHead>ラベル</TableHead>
            <TableHead>パス</TableHead>
            <TableHead className="w-12"></TableHead>
            <TableHead className="w-12"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {folders.length === 0 && (
            <TableRow>
              <TableCell colSpan={4} className="text-center text-muted-foreground py-8">
                KBフォルダが登録されていません
              </TableCell>
            </TableRow>
          )}
          {folders.map((folder) => (
            <TableRow key={folder.id}>
              <TableCell>
                <div className="flex items-center gap-1.5">
                  <FolderOpen className="h-4 w-4 text-muted-foreground" />
                  {folder.label || <span className="text-muted-foreground text-xs">-</span>}
                </div>
              </TableCell>
              <TableCell className="font-mono text-sm">{folder.path}</TableCell>
              <TableCell>
                <Button variant="ghost" size="icon" onClick={() => openEdit(folder)}>
                  <Pencil className="h-4 w-4" />
                </Button>
              </TableCell>
              <TableCell>
                <Button variant="ghost" size="icon" onClick={() => handleDelete(folder)}>
                  <Trash2 className="h-4 w-4" />
                </Button>
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>

      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>{editingId ? "KBフォルダを編集" : "KBフォルダを追加"}</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            {error && <p className="text-sm text-destructive">{error}</p>}
            <div className="space-y-1">
              <Label>フォルダパス</Label>
              <Input
                value={form.path}
                onChange={(e) => setForm({ ...form, path: e.target.value })}
                placeholder="/path/to/kb-folder"
              />
            </div>
            <div className="space-y-1">
              <Label>ラベル（任意）</Label>
              <Input
                value={form.label}
                onChange={(e) => setForm({ ...form, label: e.target.value })}
                placeholder="セキュリティポリシー関連"
              />
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
