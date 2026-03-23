import { useState, useEffect, useRef, useCallback } from "react"
import { useParams, useNavigate, Link } from "react-router-dom"
import { ArrowLeft, Upload, ChevronDown, ChevronRight, Check, Loader2 } from "lucide-react"
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
import {
  Collapsible,
  CollapsibleContent,
  CollapsibleTrigger,
} from "@/components/ui/collapsible"

type Preview = {
  col_letters: string[]
  rows: { row_num: number; cells: string[] }[]
  total_rows: number
  sheet_names: string[]
  table_count: number
  header_texts?: string[]
}

type Confidence = Record<string, "high" | "medium" | "low">
type Reasoning = Record<string, string>

type Suggestion = {
  question_col: string
  answer_col: string
  header_row: number
  data_start_row: number
  format_type: string
  choices_col: string
  remarks_col: string
  confidence: Confidence
  reasoning: Reasoning
}

type Step = "upload" | "basic" | "columns"

const FORMAT_TYPE_OPTIONS = [
  { value: "freetext", label: "自由記述型" },
  { value: "choices", label: "選択肢＋備考型" },
  { value: "assessment", label: "○/△/× 判定型" },
]

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

const COL_HIGHLIGHT: Record<string, string> = {
  question_col: "bg-green-50",
  answer_col: "bg-orange-50",
  choices_col: "bg-purple-50",
  remarks_col: "bg-gray-100",
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

  // Analysis result state
  const [preview, setPreview] = useState<Preview | null>(null)
  const [tempFileId, setTempFileId] = useState("")
  const [fileFormat, setFileFormat] = useState("xlsx")
  const [fileName, setFileName] = useState("")

  // Mapping state (editable)
  const [mapping, setMapping] = useState<Suggestion | null>(null)

  // Word hints
  const [userHint, setUserHint] = useState("")

  // Confirm
  const [qaFileName, setQaFileName] = useState("")
  const [confirming, setConfirming] = useState(false)

  useEffect(() => {
    if (!bankId) return
    apiFetch(`/api/banks/${bankId}`).then(async (res) => {
      if (res.ok) {
        const data = await res.json()
        setBankName(data.name)
      }
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
      if (!res.ok) {
        setError(data.detail || "分析に失敗しました")
        return
      }

      setPreview(data.preview)
      setTempFileId(data.temp_file_id)
      setFileFormat(data.file_format)
      setFileName(data.file_name)
      setMapping(data.suggestion)
      setQaFileName(data.file_name.replace(/\.[^.]+$/, ""))
      setStep("basic")
    } finally {
      setAnalyzing(false)
    }
  }, [file, bankId])

  const handleNextToColumns = useCallback(async () => {
    if (!mapping || !tempFileId || !bankId) return
    setAnalyzingColumns(true)
    setError("")

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/analyze/columns`, {
        method: "POST",
        body: JSON.stringify({
          temp_file_id: tempFileId,
          file_format: fileFormat,
          header_row: mapping.header_row,
          data_start_row: mapping.data_start_row,
          format_type: mapping.format_type,
          user_hint: userHint,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || "列分析に失敗しました")
        return
      }

      // Update mapping with column analysis results
      setMapping((prev) =>
        prev
          ? {
              ...prev,
              question_col: data.question_col,
              answer_col: data.answer_col,
              choices_col: data.choices_col || "",
              remarks_col: data.remarks_col || "",
              confidence: {
                ...prev.confidence,
                question_col: data.confidence?.question_col || "low",
                answer_col: data.confidence?.answer_col || "low",
                choices_col: data.confidence?.choices_col || "low",
                remarks_col: data.confidence?.remarks_col || "low",
              },
              reasoning: {
                ...prev.reasoning,
                question_col: data.reasoning?.question_col || "",
                answer_col: data.reasoning?.answer_col || "",
                choices_col: data.reasoning?.choices_col || "",
                remarks_col: data.reasoning?.remarks_col || "",
              },
            }
          : prev
      )
      setStep("columns")
    } finally {
      setAnalyzingColumns(false)
    }
  }, [mapping, tempFileId, fileFormat, bankId, userHint])

  const handleConfirm = useCallback(async () => {
    if (!mapping || !bankId || !qaFileName) return
    setConfirming(true)
    setError("")

    try {
      const res = await apiFetch(`/api/banks/${bankId}/qa-files/confirm`, {
        method: "POST",
        body: JSON.stringify({
          qa_file_name: qaFileName,
          temp_file_id: tempFileId,
          file_format: fileFormat,
          ...mapping,
        }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail || "保存に失敗しました")
        return
      }
      navigate(`/banks/${bankId}`)
    } finally {
      setConfirming(false)
    }
  }, [mapping, bankId, qaFileName, tempFileId, fileFormat, navigate])

  const updateMapping = (key: string, value: string | number) => {
    if (!mapping) return
    setMapping({ ...mapping, [key]: value })
  }

  // Determine which columns are highlighted (only in columns step)
  const highlightedCols = new Map<string, string>()
  if (step === "columns" && mapping && preview) {
    for (const [field, cssClass] of Object.entries(COL_HIGHLIGHT)) {
      const col = mapping[field as keyof Suggestion] as string
      if (col && preview.col_letters.includes(col)) {
        highlightedCols.set(col, cssClass)
      }
    }
  }

  // Build column option labels for dropdowns (docx: show header text)
  const isDocx = fileFormat === "docx"
  const colOptionLabels: Record<string, string> = {}
  const colOptionLabelsWithEmpty: Record<string, string> = { "": "(なし)" }
  if (preview) {
    const headerRow = preview.rows.find((r) => r.row_num === (mapping?.header_row || 1))
    preview.col_letters.forEach((col, ci) => {
      if (isDocx) {
        const headerText = headerRow?.cells[ci]?.trim() || ""
        const label = headerText
          ? `「${headerText}」(${ci + 1}列目)`
          : `${ci + 1}列目`
        colOptionLabels[col] = label
        colOptionLabelsWithEmpty[col] = label
      } else {
        colOptionLabels[col] = col
        colOptionLabelsWithEmpty[col] = col
      }
    })
  }

  const allLowConfidence =
    mapping?.confidence &&
    Object.values(mapping.confidence).every((c) => c === "low")

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={`/banks/${bankId}`}>
          <Button variant="ghost" size="icon">
            <ArrowLeft className="h-4 w-4" />
          </Button>
        </Link>
        <div>
          <h1 className="text-2xl font-bold">フォーマット分析</h1>
          <p className="text-sm text-muted-foreground">{bankName}</p>
        </div>
      </div>

      {/* Step indicator */}
      {step !== "upload" && (
        <div className="flex items-center gap-2 text-sm">
          <span className={step === "basic" ? "font-bold text-primary" : "text-muted-foreground"}>
            Step 1: 基本設定
          </span>
          <ChevronRight className="h-4 w-4 text-muted-foreground" />
          <span className={step === "columns" ? "font-bold text-primary" : "text-muted-foreground"}>
            Step 2: 列マッピング
          </span>
        </div>
      )}

      {error && (
        <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
          {error}
        </div>
      )}

      {/* ===== Step: Upload ===== */}
      {step === "upload" && (
        <Card>
          <CardHeader>
            <CardTitle>ファイルアップロード</CardTitle>
          </CardHeader>
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
                <p className="text-sm text-muted-foreground">
                  クリックしてファイルを選択
                </p>
              )}
              <input
                ref={fileRef}
                type="file"
                accept=".xlsx,.docx"
                className="hidden"
                onChange={(e) => setFile(e.target.files?.[0] || null)}
              />
            </div>
            <Button
              onClick={handleAnalyze}
              disabled={!file || analyzing}
              className="w-full"
            >
              {analyzing ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  AIで分析中...
                </>
              ) : (
                "AIで自動分析"
              )}
            </Button>
          </CardContent>
        </Card>
      )}

      {/* ===== Step A: Basic Settings ===== */}
      {step === "basic" && preview && mapping && (
        <>
          {allLowConfidence && (
            <div className="rounded-md bg-yellow-50 border border-yellow-200 p-3 text-sm text-yellow-800">
              自動解析の精度が低いです。手動で調整してください。
            </div>
          )}

          <PreviewTable
            preview={preview}
            mapping={mapping}
            fileFormat={fileFormat}
            fileName={fileName}
            highlightedCols={new Map()}
          />

          <Card>
            <CardHeader>
              <CardTitle>基本設定の確認</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* File format display */}
              <div className="flex items-center gap-4 text-sm">
                <span className="text-muted-foreground">ファイル形式:</span>
                <Badge variant="outline">{fileFormat.toUpperCase()}</Badge>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <MappingFieldNumber
                  label="ヘッダー行"
                  field="header_row"
                  value={mapping.header_row}
                  confidence={mapping.confidence?.header_row}
                  reasoning={mapping.reasoning?.header_row}
                  onChange={(v) => updateMapping("header_row", v)}
                />

                <MappingFieldNumber
                  label="データ開始行"
                  field="data_start_row"
                  value={mapping.data_start_row}
                  confidence={mapping.confidence?.data_start_row}
                  reasoning={mapping.reasoning?.data_start_row}
                  onChange={(v) => updateMapping("data_start_row", v)}
                />

                <MappingFieldSelect
                  label="フォーマット類型"
                  field="format_type"
                  value={mapping.format_type}
                  confidence={mapping.confidence?.format_type}
                  reasoning={mapping.reasoning?.format_type}
                  options={FORMAT_TYPE_OPTIONS}
                  onChange={(v) => updateMapping("format_type", v)}
                />

                {/* Word: table selector */}
                {isDocx && preview.table_count > 1 && (
                  <MappingFieldNumber
                    label="テーブル番号"
                    field="table_index"
                    value={1}
                    onChange={() => {}}
                  />
                )}
              </div>

              {/* Word: user hint */}
              {isDocx && (
                <div className="space-y-1.5">
                  <Label className="text-sm">構造のヒント（任意）</Label>
                  <textarea
                    className="flex w-full rounded-md border border-input bg-transparent px-3 py-2 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring min-h-[60px]"
                    value={userHint}
                    onChange={(e) => setUserHint(e.target.value)}
                    placeholder="例: 左から番号、分類、質問、回答の順です / 5列目が質問、6列目が回答です"
                  />
                  <p className="text-xs text-muted-foreground">
                    Wordファイルの構造をAIに伝えることで、列マッピングの精度が向上します。
                  </p>
                </div>
              )}

              <div className="pt-2">
                <Button
                  onClick={handleNextToColumns}
                  disabled={analyzingColumns}
                  className="w-full"
                >
                  {analyzingColumns ? (
                    <>
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                      列マッピングを分析中...
                    </>
                  ) : (
                    <>
                      次へ：列マッピング設定
                      <ChevronRight className="h-4 w-4 ml-2" />
                    </>
                  )}
                </Button>
              </div>
            </CardContent>
          </Card>
        </>
      )}

      {/* ===== Step B: Column Mapping ===== */}
      {step === "columns" && preview && mapping && (
        <>
          <PreviewTable
            preview={preview}
            mapping={mapping}
            fileFormat={fileFormat}
            fileName={fileName}
            highlightedCols={highlightedCols}
          />

          <Card>
            <CardHeader>
              <CardTitle>列マッピング設定</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <MappingField
                  label="質問列"
                  field="question_col"
                  value={mapping.question_col}
                  confidence={mapping.confidence?.question_col}
                  reasoning={mapping.reasoning?.question_col}
                  options={preview.col_letters}
                  optionLabels={colOptionLabels}
                  onChange={(v) => updateMapping("question_col", v)}
                />

                <MappingField
                  label="回答列"
                  field="answer_col"
                  value={mapping.answer_col}
                  confidence={mapping.confidence?.answer_col}
                  reasoning={mapping.reasoning?.answer_col}
                  options={preview.col_letters}
                  optionLabels={colOptionLabels}
                  onChange={(v) => updateMapping("answer_col", v)}
                />

                {mapping.format_type !== "freetext" && (
                  <MappingField
                    label={
                      mapping.format_type === "assessment"
                        ? "判定欄列"
                        : "選択肢列"
                    }
                    field="choices_col"
                    value={mapping.choices_col}
                    confidence={mapping.confidence?.choices_col}
                    reasoning={mapping.reasoning?.choices_col}
                    options={["", ...preview.col_letters]}
                    optionLabels={colOptionLabelsWithEmpty}
                    onChange={(v) => updateMapping("choices_col", v)}
                  />
                )}

                {mapping.format_type !== "freetext" && (
                  <MappingField
                    label="備考列"
                    field="remarks_col"
                    value={mapping.remarks_col}
                    confidence={mapping.confidence?.remarks_col}
                    reasoning={mapping.reasoning?.remarks_col}
                    options={["", ...preview.col_letters]}
                    optionLabels={colOptionLabelsWithEmpty}
                    onChange={(v) => updateMapping("remarks_col", v)}
                  />
                )}
              </div>
            </CardContent>
          </Card>

          {/* Confirm */}
          <Card>
            <CardContent className="space-y-4 pt-6">
              <div className="space-y-2">
                <Label>QAファイル名</Label>
                <Input
                  value={qaFileName}
                  onChange={(e) => setQaFileName(e.target.value)}
                  placeholder="例: セキュリティチェックシート"
                />
              </div>
              <div className="flex gap-3">
                <Button
                  variant="outline"
                  onClick={() => setStep("basic")}
                >
                  <ArrowLeft className="h-4 w-4 mr-2" />
                  戻る
                </Button>
                <Button
                  onClick={handleConfirm}
                  disabled={confirming || !qaFileName}
                  className="flex-1"
                >
                  {confirming ? (
                    <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  ) : (
                    <Check className="h-4 w-4 mr-2" />
                  )}
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
  preview,
  mapping,
  fileFormat,
  fileName,
  highlightedCols,
}: {
  preview: Preview
  mapping: Suggestion
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
          <span className="text-sm font-normal text-muted-foreground">
            {fileName} ({preview.total_rows}行)
          </span>
        </CardTitle>
      </CardHeader>
      <CardContent>
        <div className="overflow-x-auto max-h-[400px] overflow-y-auto border border-gray-300 rounded">
          <table className="w-full border-collapse text-xs">
            <thead>
              <tr>
                <th className="sticky left-0 z-10 w-10 bg-gray-100 border border-gray-300 px-1.5 py-1 text-center text-muted-foreground font-normal">
                  #
                </th>
                {preview.col_letters.map((col, ci) => {
                  const colLabel = isDocx ? `${ci + 1}列目` : col
                  const highlight = highlightedCols.get(col) || ""
                  const roleLabel = Object.entries(COL_HIGHLIGHT).find(
                    ([field]) =>
                      (mapping[field as keyof Suggestion] as string) === col
                  )?.[0]
                    ?.replace("_col", "")
                    .replace("question", "質問")
                    .replace("answer", "回答")
                    .replace("choices", "選択肢")
                    .replace("remarks", "備考")
                  return (
                    <th
                      key={col}
                      className={`min-w-[80px] bg-gray-100 border border-gray-300 px-1.5 py-1 text-center font-medium ${highlight}`}
                    >
                      <div className="flex items-center justify-center gap-1">
                        {colLabel}
                        {roleLabel && (
                          <span className="text-[9px] opacity-60">
                            {roleLabel}
                          </span>
                        )}
                      </div>
                    </th>
                  )
                })}
              </tr>
            </thead>
            <tbody>
              {preview.rows.map((row) => (
                <tr
                  key={row.row_num}
                  className={
                    row.row_num === mapping.header_row
                      ? "bg-blue-50 font-medium"
                      : row.row_num < mapping.data_start_row
                        ? "bg-gray-50/50 text-muted-foreground"
                        : ""
                  }
                >
                  <td className="sticky left-0 z-10 bg-gray-100 border border-gray-300 px-1.5 py-0.5 text-center text-muted-foreground">
                    {row.row_num}
                  </td>
                  {row.cells.map((cell, ci) => (
                    <td
                      key={ci}
                      className={`border border-gray-200 px-1.5 py-0.5 truncate max-w-[200px] ${
                        highlightedCols.get(preview.col_letters[ci]) || ""
                      }`}
                      title={cell}
                    >
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

function MappingField({
  label,
  field,
  value,
  confidence,
  reasoning,
  options,
  optionLabels,
  onChange,
}: {
  label: string
  field: string
  value: string
  confidence?: string
  reasoning?: string
  options: string[]
  optionLabels?: Record<string, string>
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Label className="text-sm">{label}</Label>
        {confidence && (
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${CONFIDENCE_COLORS[confidence] || ""}`}
          >
            信頼度: {CONFIDENCE_LABELS[confidence] || confidence}
          </Badge>
        )}
      </div>
      <select
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt} value={opt}>
            {optionLabels?.[opt] ?? (opt || "(なし)")}
          </option>
        ))}
      </select>
      {reasoning && (
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
            <ChevronDown className="h-3 w-3" />
            AI判断理由
          </CollapsibleTrigger>
          <CollapsibleContent className="text-xs text-muted-foreground mt-1 pl-4">
            {reasoning}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

function MappingFieldNumber({
  label,
  field,
  value,
  confidence,
  reasoning,
  onChange,
}: {
  label: string
  field: string
  value: number
  confidence?: string
  reasoning?: string
  onChange: (v: number) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Label className="text-sm">{label}</Label>
        {confidence && (
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${CONFIDENCE_COLORS[confidence] || ""}`}
          >
            信頼度: {CONFIDENCE_LABELS[confidence] || confidence}
          </Badge>
        )}
      </div>
      <Input
        type="number"
        min={1}
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value) || 1)}
      />
      {reasoning && (
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
            <ChevronDown className="h-3 w-3" />
            AI判断理由
          </CollapsibleTrigger>
          <CollapsibleContent className="text-xs text-muted-foreground mt-1 pl-4">
            {reasoning}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}

function MappingFieldSelect({
  label,
  field,
  value,
  confidence,
  reasoning,
  options,
  onChange,
}: {
  label: string
  field: string
  value: string
  confidence?: string
  reasoning?: string
  options: { value: string; label: string }[]
  onChange: (v: string) => void
}) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center gap-2">
        <Label className="text-sm">{label}</Label>
        {confidence && (
          <Badge
            variant="outline"
            className={`text-[10px] px-1.5 py-0 ${CONFIDENCE_COLORS[confidence] || ""}`}
          >
            信頼度: {CONFIDENCE_LABELS[confidence] || confidence}
          </Badge>
        )}
      </div>
      <select
        className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 py-1 text-sm shadow-xs transition-colors focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
        value={value}
        onChange={(e) => onChange(e.target.value)}
      >
        {options.map((opt) => (
          <option key={opt.value} value={opt.value}>
            {opt.label}
          </option>
        ))}
      </select>
      {reasoning && (
        <Collapsible>
          <CollapsibleTrigger className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground cursor-pointer">
            <ChevronDown className="h-3 w-3" />
            AI判断理由
          </CollapsibleTrigger>
          <CollapsibleContent className="text-xs text-muted-foreground mt-1 pl-4">
            {reasoning}
          </CollapsibleContent>
        </Collapsible>
      )}
    </div>
  )
}
