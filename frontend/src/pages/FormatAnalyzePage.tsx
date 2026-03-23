import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { ArrowLeft, Upload, ChevronRight, Check, Loader2, Plus, Trash2 } from "lucide-react"
import { apiFetch } from "@/lib/httpClient"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"

type TableSummary = {
  index: number
  rows: number
  cols: number
  header: string
}

type Preview = {
  col_letters: string[]
  rows: { row_num: number; cells: string[] }[]
  total_rows: number
  sheet_names: string[]
  table_count: number
  header_texts?: string[]
  tables_summary?: TableSummary[]
  best_table_index?: number
  selected_table_index?: number
}

type Confidence = Record<string, string>
type Reasoning = Record<string, string>

type BasicSuggestion = {
  header_row: number
  data_start_row: number
  confidence: Confidence
  reasoning: Reasoning
}

type ColumnDef = {
  col: string
  role: string
  description: string
}

type Step = "upload" | "basic" | "columns"

const ROLE_OPTIONS = [
  { value: "", label: "── 読み取り列（システムが参照）──", disabled: true },
  { value: "question", label: "質問・確認事項" },
  { value: "category", label: "分類・カテゴリ" },
  { value: "number", label: "番号" },
  { value: "reference", label: "参照情報（判断基準・エビデンス・設定例等）" },
  { value: "remarks", label: "備考" },
  { value: "", label: "── 書き込み列（システムが記入）──", disabled: true },
  { value: "answer", label: "回答欄（テキスト回答）" },
  { value: "judgment", label: "判定欄（○/△/×等の記号）" },
  { value: "", label: "── その他 ──", disabled: true },
  { value: "other", label: "その他" },
] as const

// 読み取り=青系、書き込み=オレンジ系、その他=グレー系
const ROLE_COLORS: Record<string, string> = {
  // 読み取り列（青系）
  question: "bg-blue-50 border-blue-200",
  category: "bg-blue-50 border-blue-200",
  number: "bg-blue-50 border-blue-200",
  reference: "bg-blue-50 border-blue-200",
  remarks: "bg-blue-50 border-blue-200",
  // 書き込み列（オレンジ系）
  answer: "bg-orange-50 border-orange-200",
  judgment: "bg-orange-50 border-orange-200",
  // その他（グレー系）
  other: "bg-neutral-50 border-neutral-200",
}

const COL_HIGHLIGHT_BY_ROLE: Record<string, string> = {
  // 読み取り列（青系）
  question: "bg-blue-50",
  category: "bg-blue-50",
  number: "bg-blue-50",
  reference: "bg-blue-50",
  remarks: "bg-blue-50",
  // 書き込み列（オレンジ系）
  answer: "bg-orange-50",
  judgment: "bg-orange-50",
}

const CONFIDENCE_COLORS: Record<string, string> = {
  high: "bg-green-100 text-green-800 border-green-300",
  medium: "bg-yellow-100 text-yellow-800 border-yellow-300",
  low: "bg-red-100 text-red-800 border-red-300",
}

const CONFIDENCE_LABELS: Record<string, string> = {
  high: "高",
  medium: "中",
  low: "低",
}

export default function FormatAnalyzePage() {
  const { bankId } = useParams()
  const navigate = useNavigate()
  const fileRef = useRef<HTMLInputElement>(null)

  const [step, setStep] = useState<Step>("upload")
  const [bankName, setBankName] = useState("")
  const [file, setFile] = useState<File | null>(null)
  const [analyzing, setAnalyzing] = useState(false)
  const [analyzingColumns, setAnalyzingColumns] = useState(false)
  const [error, setError] = useState("")

  const [preview, setPreview] = useState<Preview | null>(null)
  const [tempFileId, setTempFileId] = useState("")
  const [fileFormat, setFileFormat] = useState("xlsx")
  const [fileName, setFileName] = useState("")

  // Basic settings (Step A)
  const [basicSuggestion, setBasicSuggestion] = useState<BasicSuggestion | null>(null)
  const [headerRow, setHeaderRow] = useState(1)
  const [dataStartRow, setDataStartRow] = useState(2)

  // Column definitions (Step B)
  const [columnDefs, setColumnDefs] = useState<ColumnDef[]>([])
  const [rowStructure, setRowStructure] = useState("")

  // Word
  const [selectedTableIndex, setSelectedTableIndex] = useState(0)
  const [reanalyzing, setReanalyzing] = useState(false)
  const [userHint, setUserHint] = useState("")

  const [qaFileName, setQaFileName] = useState("")
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!bankId) return
    apiFetch(`/api/banks/${bankId}`).then(async (res) => {
      if (res.ok) setBankName((await res.json()).name)
    })
  }, [bankId])

  const handleAnalyze = useCallback(async () => {
    if (!file || !bankId) return
    setAnalyzing(true)
    setError("")

    const formData = new FormData()
    formData.append("file", file)

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/analyze`, {
        method: "POST",
        body: formData,
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || "分析に失敗しました"); return }

      setPreview(data.preview)
      setTempFileId(data.temp_file_id)
      setFileFormat(data.file_format)
      setFileName(data.file_name)
      setHeaderRow(data.suggestion.header_row)
      setDataStartRow(data.suggestion.data_start_row)
      setBasicSuggestion({
        header_row: data.suggestion.header_row,
        data_start_row: data.suggestion.data_start_row,
        confidence: data.suggestion.confidence || {},
        reasoning: data.suggestion.reasoning || {},
      })
      setSelectedTableIndex(data.preview.selected_table_index ?? data.preview.best_table_index ?? 0)
      setQaFileName(data.file_name.replace(/\.[^.]+$/, ""))
      setStep("basic")
    } finally {
      setAnalyzing(false)
    }
  }, [file, bankId])

  const handleTableChange = useCallback(async (newIndex: number) => {
    if (!tempFileId || !bankId) return
    setSelectedTableIndex(newIndex)
    setReanalyzing(true)
    setError("")

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/analyze/reparse`, {
        method: "POST",
        body: JSON.stringify({ temp_file_id: tempFileId, file_format: fileFormat, table_index: newIndex }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || "テーブル切替に失敗しました"); return }
      setPreview(data.preview)
      setHeaderRow(data.suggestion.header_row)
      setDataStartRow(data.suggestion.data_start_row)
      setBasicSuggestion({
        header_row: data.suggestion.header_row,
        data_start_row: data.suggestion.data_start_row,
        confidence: data.suggestion.confidence || {},
        reasoning: data.suggestion.reasoning || {},
      })
    } finally {
      setReanalyzing(false)
    }
  }, [tempFileId, bankId, fileFormat])

  const handleNextToColumns = useCallback(async () => {
    if (!tempFileId || !bankId) return
    setAnalyzingColumns(true)
    setError("")

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/analyze/columns`, {
        method: "POST",
        body: JSON.stringify({
          temp_file_id: tempFileId,
          file_format: fileFormat,
          table_index: selectedTableIndex,
          header_row: headerRow,
          data_start_row: dataStartRow,
          user_hint: userHint,
        }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || "列分析に失敗しました"); return }
      setColumnDefs(data.column_definitions || [])
      setRowStructure(data.row_structure || "")
      setStep("columns")
    } finally {
      setAnalyzingColumns(false)
    }
  }, [tempFileId, bankId, fileFormat, selectedTableIndex, headerRow, dataStartRow, userHint])

  const handleConfirm = useCallback(async () => {
    if (!bankId || !qaFileName) return
    setConfirming(true)
    setError("")

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/confirm`, {
        method: "POST",
        body: JSON.stringify({
          qa_file_name: qaFileName,
          temp_file_id: tempFileId,
          file_format: fileFormat,
          header_row: headerRow,
          data_start_row: dataStartRow,
          table_index: selectedTableIndex,
          column_definitions: columnDefs,
          row_structure: rowStructure,
        }),
      })
      const data = await res.json()
      if (!res.ok) { setError(data.detail || "保存に失敗しました"); return }
      navigate(`/banks/${bankId}`)
    } finally {
      setConfirming(false)
    }
  }, [bankId, qaFileName, tempFileId, fileFormat, headerRow, dataStartRow, selectedTableIndex, columnDefs, rowStructure, navigate])

  // Column highlights for preview table
  const highlightedCols = new Map<string, string>()
  if (step === "columns" && preview) {
    for (const def of columnDefs) {
      const color = COL_HIGHLIGHT_BY_ROLE[def.role]
      if (color && preview.col_letters.includes(def.col)) {
        highlightedCols.set(def.col, color)
      }
    }
  }

  // Column option labels for docx
  const isDocx = fileFormat === "docx"
  const colOptionLabels: Record<string, string> = {}
  if (preview) {
    const hRow = preview.rows.find((r) => r.row_num === headerRow)
    preview.col_letters.forEach((col, ci) => {
      if (isDocx) {
        const ht = hRow?.cells[ci]?.trim() || ""
        colOptionLabels[col] = ht ? `「${ht}」(${ci + 1}列目)` : `${ci + 1}列目`
      } else {
        colOptionLabels[col] = col
      }
    })
  }

  const updateColDef = (index: number, field: keyof ColumnDef, value: string) => {
    setColumnDefs((prev) => prev.map((d, i) => i === index ? { ...d, [field]: value } : d))
  }
  const removeColDef = (index: number) => {
    setColumnDefs((prev) => prev.filter((_, i) => i !== index))
  }
  const addColDef = () => {
    const usedCols = new Set(columnDefs.map((d) => d.col))
    const nextCol = preview?.col_letters.find((c) => !usedCols.has(c)) || "A"
    setColumnDefs((prev) => [...prev, { col: nextCol, role: "other", description: "" }])
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={`/banks/${bankId}`}>
          <Button variant="ghost" size="icon"><ArrowLeft className="h-4 w-4" /></Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">フォーマット分析</h1>
          <p className="text-sm text-muted-foreground">{bankName}</p>
        </div>
      </div>

      {step !== "upload" && (
        <div className="flex items-center gap-2 text-sm">
          <span className={step === "basic" ? "font-bold text-primary" : "text-muted-foreground"}>Step 1: 基本設定</span>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <span className={step === "columns" ? "font-bold text-primary" : "text-muted-foreground"}>Step 2: 列定義</span>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">{error}</div>
      )}

      {/* ===== Upload ===== */}
      {step === "upload" && (
        <Card>
          <CardHeader><CardTitle>ファイルアップロード</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-muted-foreground">
              アンケートファイル（xlsx/docx）をアップロードすると、AIがフォーマットを自動解析します。
            </p>
            <div
              className="border-2 border-dashed rounded-lg p-8 text-center cursor-pointer hover:border-primary/50 transition-colors"
              onClick={() => fileRef.current?.click()}
            >
              <Upload className="h-8 w-8 mx-auto mb-2 text-muted-foreground" />
              {file ? (
                <p className="text-sm font-medium">{file.name}</p>
              ) : (
                <p className="text-sm text-muted-foreground">クリックしてファイルを選択</p>
              )}
              <input ref={fileRef} type="file" accept=".xlsx,.docx" className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)} />
            </div>
            <Button onClick={handleAnalyze} disabled={!file || analyzing} className="w-full">
              {analyzing ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />AIで分析中...</>) : "AIで自動分析"}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ===== Step A: Basic Settings ===== */}
      {step === "basic" && preview && (
        <>
          <PreviewTable preview={preview} headerRow={headerRow} dataStartRow={dataStartRow}
            fileFormat={fileFormat} fileName={fileName} highlightedCols={new Map()} />

          <Card>
            <CardHeader><CardTitle>基本設定の確認</CardTitle></CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">ファイル形式:</span>
                <Badge variant="outline">{fileFormat.toUpperCase()}</Badge>
              </div>

              {/* Word: table selector */}
              {isDocx && preview.tables_summary && preview.tables_summary.length > 1 && (
                <div className="space-y-1.5">
                  <Label className="text-sm">対象テーブル</Label>
                  <select className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm"
                    value={selectedTableIndex} onChange={(e) => handleTableChange(parseInt(e.target.value))} disabled={reanalyzing}>
                    {preview.tables_summary.map((t) => (
                      <option key={t.index} value={t.index}>
                        テーブル{t.index + 1}: {t.rows}行×{t.cols}列 — {t.header.slice(0, 40)}{t.header.length > 40 ? "..." : ""}
                        {t.index === (preview.best_table_index ?? 0) ? " (自動選択)" : ""}
                      </option>
                    ))}
                  </select>
                  {reanalyzing && <p className="text-xs text-muted-foreground flex items-center gap-1"><Loader2 className="h-3 w-3 animate-spin" />再分析中...</p>}
                </div>
              )}

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Label className="text-sm">ヘッダー行</Label>
                    {basicSuggestion?.confidence?.header_row && (
                      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${CONFIDENCE_COLORS[basicSuggestion.confidence.header_row] || ""}`}>
                        信頼度: {CONFIDENCE_LABELS[basicSuggestion.confidence.header_row] || ""}
                      </Badge>
                    )}
                  </div>
                  <Input type="number" min={1} value={headerRow} onChange={(e) => setHeaderRow(parseInt(e.target.value) || 1)} />
                </div>
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <Label className="text-sm">データ開始行</Label>
                    {basicSuggestion?.confidence?.data_start_row && (
                      <Badge variant="outline" className={`text-[10px] px-1.5 py-0 ${CONFIDENCE_COLORS[basicSuggestion.confidence.data_start_row] || ""}`}>
                        信頼度: {CONFIDENCE_LABELS[basicSuggestion.confidence.data_start_row] || ""}
                      </Badge>
                    )}
                  </div>
                  <Input type="number" min={1} value={dataStartRow} onChange={(e) => setDataStartRow(parseInt(e.target.value) || 1)} />
                </div>
              </div>

              {/* Word: hint */}
              {isDocx && (
                <div className="space-y-1.5">
                  <Label className="text-sm">構造のヒント（任意）</Label>
                  <textarea className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[60px]"
                    value={userHint} onChange={(e) => setUserHint(e.target.value)}
                    placeholder="例: 左から番号、分類、質問、回答の順です" />
                  <p className="text-xs text-muted-foreground">Wordファイルの構造をAIに伝えることで、列定義の精度が向上します。</p>
                </div>
              )}

              <Button onClick={handleNextToColumns} disabled={analyzingColumns} className="w-full">
                {analyzingColumns ? (<><Loader2 className="h-4 w-4 mr-2 animate-spin" />列定義を分析中...</>) : (<>次へ：列定義<ChevronRight className="h-4 w-4 ml-2" /></>)}
              </Button>
            </CardContent>
          </Card>
        </>
      )}

      {/* ===== Step B: Column Definitions ===== */}
      {step === "columns" && preview && (
        <>
          <PreviewTable preview={preview} headerRow={headerRow} dataStartRow={dataStartRow}
            fileFormat={fileFormat} fileName={fileName} highlightedCols={highlightedCols} />

          <Card>
            <CardHeader>
              <CardTitle>列定義</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                各列がアンケートのどの要素に対応するかを定義します。この情報は質問の抽出・回答の記入先の特定・回答生成AIへの指示に使用されます。
              </p>
              <p className="text-xs text-muted-foreground mt-1 bg-blue-50 rounded px-2 py-1">
                以下はAIが自動分析した提案です。内容を確認し、必要に応じて修正・追加・削除してください。
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              {/* Column headers */}
              <div className="flex items-center gap-2 px-2 text-xs font-medium text-muted-foreground">
                <span className="w-40">列名</span>
                <span className="w-64">意味（選択式）</span>
                <span className="flex-1">意味（補足説明）</span>
                <span className="w-8" />
              </div>

              {columnDefs.length === 0 && (
                <p className="text-sm text-muted-foreground py-2">列定義がありません。「追加」ボタンで列を登録してください。</p>
              )}
              {columnDefs.map((def, i) => (
                <div key={i} className={`flex items-center gap-2 p-2 rounded border ${ROLE_COLORS[def.role] || "border-border"}`}>
                  <select className="h-8 rounded border border-input bg-transparent px-2 text-sm w-40 shrink-0"
                    value={def.col} onChange={(e) => updateColDef(i, "col", e.target.value)}>
                    {preview.col_letters.map((c) => (
                      <option key={c} value={c}>{colOptionLabels[c] || c}</option>
                    ))}
                  </select>
                  <select className="h-8 rounded border border-input bg-transparent px-2 text-sm w-64 shrink-0"
                    value={def.role} onChange={(e) => updateColDef(i, "role", e.target.value)}>
                    {ROLE_OPTIONS.map((r, ri) => (
                      r.disabled
                        ? <option key={ri} value="" disabled>{r.label}</option>
                        : <option key={r.value} value={r.value}>{r.label}</option>
                    ))}
                  </select>
                  <Input className="h-8 flex-1 text-sm" placeholder="補足説明（例: 規定内容・確認事項を記載）"
                    value={def.description} onChange={(e) => updateColDef(i, "description", e.target.value)} />
                  <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0" onClick={() => removeColDef(i)}>
                    <Trash2 className="h-3 w-3" />
                  </Button>
                </div>
              ))}

              <Button variant="outline" size="sm" onClick={addColDef} className="mt-2">
                <Plus className="h-3 w-3 mr-1" />列定義を追加
              </Button>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>行構造の説明</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">
                このアンケートの各行にどのような情報が入るかを説明してください。回答生成AIにプロンプトとして渡されます。
              </p>
            </CardHeader>
            <CardContent className="space-y-3">
              <textarea className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm min-h-[100px]"
                value={rowStructure} onChange={(e) => setRowStructure(e.target.value)}
                placeholder={"例:\n各行は1つの確認項目（質問）に対応する。A列に通番、B-C列に分類、E列に質問（規定内容）、F列に回答を記入する。\nただし、大分類の見出し行（A列に番号がなくB列にカテゴリ名のみ記載）が途中に挿入されており、これは質問ではない。"} />
              <p className="text-xs text-muted-foreground bg-blue-50 rounded px-2 py-1">
                上記はAIが自動生成した説明です。特に、質問ではない行（大分類の見出し行など）がある場合はその旨を記載すると、AIの回答精度が向上します。
              </p>
            </CardContent>
          </Card>

          <Card>
            <CardContent className="space-y-4 pt-6">
              <div className="space-y-2">
                <Label>QAファイル名</Label>
                <Input value={qaFileName} onChange={(e) => setQaFileName(e.target.value)} placeholder="例: セキュリティチェックシート" />
              </div>
              <div className="flex gap-3">
                <Button variant="outline" onClick={() => setStep("basic")}>
                  <ArrowLeft className="h-4 w-4 mr-2" />戻る
                </Button>
                <Button onClick={handleConfirm} disabled={confirming || !qaFileName || columnDefs.length === 0} className="flex-1">
                  {confirming ? <Loader2 className="h-4 w-4 mr-2 animate-spin" /> : <Check className="h-4 w-4 mr-2" />}
                  確定して保存
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}

/* ---- Sub-components ---- */

function PreviewTable({
  preview, headerRow, dataStartRow, fileFormat, fileName, highlightedCols,
}: {
  preview: Preview
  headerRow: number
  dataStartRow: number
  fileFormat: string
  fileName: string
  highlightedCols: Map<string, string>
}) {
  const isDocx = fileFormat === "docx"
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center justify-between">
          <span>ファイルプレビュー</span>
          <span className="text-sm font-normal text-muted-foreground">{fileName} ({preview.total_rows}行)</span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto max-h-[400px] overflow-y-auto border border-gray-300 rounded">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 w-10 bg-gray-100 border border-gray-300 px-1.5 py-1 text-center text-muted-foreground font-normal">#</th>
                {preview.col_letters.map((col, ci) => {
                  const colLabel = isDocx ? `${ci + 1}列目` : col
                  const highlight = highlightedCols.get(col) || ""
                  return (
                    <th key={col} className={`min-w-[80px] bg-gray-100 border border-gray-300 px-1.5 py-1 text-center font-medium ${highlight}`}>
                      {colLabel}
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr key={row.row_num} className={
                  row.row_num === headerRow ? "bg-blue-50 font-medium"
                    : row.row_num < dataStartRow ? "bg-gray-50/50 text-muted-foreground" : ""
                }>
                  <td className="sticky left-0 z-10 bg-gray-100 border border-gray-300 px-1.5 py-0.5 text-center text-muted-foreground">{row.row_num}</td>
                  {row.cells.map((cell, ci) => (
                    <td key={ci} className={`border border-gray-200 px-1.5 py-0.5 truncate max-w-[200px] ${highlightedCols.get(preview.col_letters[ci]) || ""}`} title={cell}>
                      {cell || <span className="text-muted-foreground">-</span>}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </CardContent>
    </Card>
  )
}
