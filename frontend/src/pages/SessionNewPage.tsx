import { useState, useEffect, useRef } from "react"
import { useNavigate } from "react-router-dom"
import { Upload } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Label } from "@/components/ui/label"
import { StepIndicator } from "@/components/StepIndicator"

type Bank = {
  id: number
  name: string
  code: string
}

type QaFile = {
  id: number
  qa_file_name: string
  file_format: string
}

export default function SessionNewPage() {
  const [banks, setBanks] = useState<Bank[]>([])
  const [bankId, setBankId] = useState<number | "">("")
  const [qaFiles, setQaFiles] = useState<QaFile[]>([])
  const [qaFileId, setQaFileId] = useState<number | "">("")
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    apiFetch("/api/banks").then(async (res) => {
      if (res.ok) setBanks(await res.json())
    })
  }, [])

  useEffect(() => {
    if (!bankId) {
      setQaFiles([])
      setQaFileId("")
      return
    }
    apiFetch(`/api/banks/${bankId}/qa-files`).then(async (res) => {
      if (res.ok) {
        const files = await res.json()
        setQaFiles(files)
        setQaFileId(files.length === 1 ? files[0].id : "")
      }
    })
  }, [bankId])

  const handleSubmit = async () => {
    if (!bankId || !file) return
    setLoading(true)
    setError("")

    const formData = new FormData()
    formData.append("file", file)

    const params = new URLSearchParams({ bank_id: String(bankId) })
    if (qaFileId) params.set("qa_file_id", String(qaFileId))

    const res = await apiFetch(`/api/sessions?${params}`, {
      method: "POST",
      body: formData,
    })
    const data = await res.json()
    if (res.ok) {
      navigate(`/sessions/${data.session_id}/step2`)
    } else {
      setError(data.detail || "ワークフロー作成に失敗しました")
    }
    setLoading(false)
  }

  const selectedQf = qaFiles.find((qf) => qf.id === qaFileId)

  return (
    <div className="max-w-2xl mx-auto space-y-6">
      <StepIndicator current={1} />

      <div className="space-y-4">
        <div className="space-y-2">
          <Label>銀行を選択</Label>
          <select
            className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
            value={bankId}
            onChange={(e) => setBankId(e.target.value ? Number(e.target.value) : "")}
          >
            <option value="">選択してください</option>
            {banks.map((b) => (
              <option key={b.id} value={b.id}>{b.name} ({b.code})</option>
            ))}
          </select>
        </div>

        {bankId && qaFiles.length > 0 && (
          <div className="space-y-2">
            <Label>金融機関から受領したアンケートを選択</Label>
            <select
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
              value={qaFileId}
              onChange={(e) => setQaFileId(e.target.value ? Number(e.target.value) : "")}
            >
              <option value="">選択してください</option>
              {qaFiles.map((qf) => (
                <option key={qf.id} value={qf.id}>
                  {qf.qa_file_name} ({qf.file_format.toUpperCase()})
                </option>
              ))}
            </select>
            {selectedQf && (
              <p className="text-xs text-muted-foreground">
                形式: {selectedQf.file_format.toUpperCase()}
              </p>
            )}
          </div>
        )}

        <div className="space-y-2">
          <Label>質問票ファイル</Label>
          <div className="border-2 border-dashed border-border rounded-lg p-8 text-center">
            <input
              ref={fileRef}
              type="file"
              accept=".xlsx,.docx"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="hidden"
            />
            {file ? (
              <div className="space-y-2">
                <p className="font-medium">{file.name}</p>
                <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
                  変更
                </Button>
              </div>
            ) : (
              <div className="space-y-2">
                <Upload className="h-8 w-8 mx-auto text-muted-foreground" />
                <p className="text-sm text-muted-foreground">質問票ファイルをアップロード</p>
                <Button variant="outline" size="sm" onClick={() => fileRef.current?.click()}>
                  ファイルを選択
                </Button>
              </div>
            )}
          </div>
        </div>

        {error && <p className="text-sm text-destructive">{error}</p>}

        <Button
          onClick={handleSubmit}
          disabled={!bankId || !file || loading}
          className="w-full"
        >
          {loading ? "処理中..." : "質問を抽出してStep2へ進む"}
        </Button>
      </div>
    </div>
  )
}
