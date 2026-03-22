export type DiffSegment = {
  type: "same" | "added" | "removed"
  text: string
}

/**
 * Compute a word-level diff between two strings using LCS.
 * Returns segments tagged as same/added/removed.
 */
export function diffWords(oldText: string, newText: string): DiffSegment[] {
  const oldTokens = tokenize(oldText)
  const newTokens = tokenize(newText)

  const lcs = computeLCS(oldTokens, newTokens)

  const segments: DiffSegment[] = []
  let oi = 0
  let ni = 0

  for (const [lo, ln] of lcs) {
    if (oi < lo) {
      segments.push({ type: "removed", text: oldTokens.slice(oi, lo).join("") })
    }
    if (ni < ln) {
      segments.push({ type: "added", text: newTokens.slice(ni, ln).join("") })
    }
    segments.push({ type: "same", text: oldTokens[lo] })
    oi = lo + 1
    ni = ln + 1
  }

  if (oi < oldTokens.length) {
    segments.push({ type: "removed", text: oldTokens.slice(oi).join("") })
  }
  if (ni < newTokens.length) {
    segments.push({ type: "added", text: newTokens.slice(ni).join("") })
  }

  return segments
}

function tokenize(text: string): string[] {
  return [...text]
}

function computeLCS(a: string[], b: string[]): [number, number][] {
  const m = a.length
  const n = b.length
  const dp: number[][] = Array.from({ length: m + 1 }, () => Array(n + 1).fill(0))

  for (let i = m - 1; i >= 0; i--) {
    for (let j = n - 1; j >= 0; j--) {
      if (a[i] === b[j]) {
        dp[i][j] = dp[i + 1][j + 1] + 1
      } else {
        dp[i][j] = Math.max(dp[i + 1][j], dp[i][j + 1])
      }
    }
  }

  const result: [number, number][] = []
  let i = 0
  let j = 0
  while (i < m && j < n) {
    if (a[i] === b[j]) {
      result.push([i, j])
      i++
      j++
    } else if (dp[i + 1][j] >= dp[i][j + 1]) {
      i++
    } else {
      j++
    }
  }
  return result
}
