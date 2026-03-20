const steps = [
  { no: 1, label: "質問票アップロード" },
  { no: 2, label: "過去回答マッチング" },
  { no: 3, label: "共通回答マッチング" },
  { no: 4, label: "AI回答生成" },
  { no: 5, label: "最終確認" },
]

export function StepIndicator({ current }: { current: number }) {
  return (
    <div className="flex items-center gap-1 mb-6">
      {steps.map((step, i) => (
        <div key={step.no} className="flex items-center">
          <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full text-sm ${
            step.no === current
              ? "bg-primary text-primary-foreground font-medium"
              : step.no < current
              ? "bg-primary/10 text-primary"
              : "bg-muted text-muted-foreground"
          }`}>
            <span className="text-xs font-mono">{step.no}</span>
            <span>{step.label}</span>
          </div>
          {i < steps.length - 1 && (
            <div className={`w-6 h-px mx-1 ${
              step.no < current ? "bg-primary" : "bg-border"
            }`} />
          )}
        </div>
      ))}
    </div>
  )
}
