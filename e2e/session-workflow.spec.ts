import { test, expect } from "@playwright/test"

test.describe("Session Workflow", () => {
  // Helper: create a bank via API
  async function createBank(request: any) {
    const res = await request.post("http://localhost:8000/api/banks", {
      data: {
        name: "ワークフロー銀行",
        code: "wf-bank",
        file_format: "xlsx",
        question_col: "D",
        answer_col: "E",
        header_row: 1,
        data_start_row: 2,
      },
    })
    if (res.status() === 409) {
      // Already exists, fetch the list
      const listRes = await request.get("http://localhost:8000/api/banks")
      const banks = await listRes.json()
      return banks.find((b: any) => b.code === "wf-bank")?.id || 1
    }
    const data = await res.json()
    return data.id
  }

  test("Step1: shows bank selector and file upload", async ({ page }) => {
    await page.goto("/sessions/new")
    await expect(page.getByText("銀行を選択")).toBeVisible()
    await expect(page.getByText("質問票ファイル", { exact: true })).toBeVisible()
  })

  test("Step1: submit button disabled without bank and file", async ({ page }) => {
    await page.goto("/sessions/new")
    const submitBtn = page.getByRole("button", { name: "質問を抽出してStep2へ進む" })
    await expect(submitBtn).toBeDisabled()
  })

  test("Step1: creates session and navigates to Step2", async ({ page, request }) => {
    const bankId = await createBank(request)

    // Mock session creation
    await page.route("**/api/sessions?bank_id=*", async (route) => {
      if (route.request().method() === "POST") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ session_id: 1, question_count: 3 }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto("/sessions/new")
    await page.waitForTimeout(500)

    // Select bank
    const select = page.locator("select")
    await select.selectOption({ index: 1 })

    // Upload file
    const fileInput = page.locator('input[type="file"]')
    await fileInput.setInputFiles({
      name: "test-questionnaire.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("fake-xlsx"),
    })

    await page.getByRole("button", { name: "質問を抽出してStep2へ進む" }).click()
    await expect(page).toHaveURL(/\/sessions\/\d+\/step2/)
  })

  test("Step2: shows matching button", async ({ page }) => {
    // Mock step2 results
    await page.route("**/step2/results", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { question_no: 1, question_text: "セキュリティポリシーは策定されていますか？", major: "セキュリティ管理", minor: "基本方針", past_question_text: "", past_answer_text: "", matched_past_qa_id: null, answer_source: "pending" },
        ]),
      })
    })

    await page.goto("/sessions/1/step2")
    await expect(page.getByRole("button", { name: "マッチング実行" })).toBeVisible()
  })

  test("Step2: runs matching and shows results", async ({ page }) => {
    let matched = false

    await page.route("**/step2/results", async (route) => {
      const questions = [
        { question_no: 1, question_text: "セキュリティポリシーは？", major: "セキュリティ", minor: "", past_question_text: matched ? "セキュリティポリシーについて" : "", past_answer_text: matched ? "策定済みです" : "", matched_past_qa_id: matched ? 1 : null, answer_source: "pending" },
        { question_no: 2, question_text: "バックアップは？", major: "運用", minor: "", past_question_text: "", past_answer_text: "", matched_past_qa_id: null, answer_source: "pending" },
      ]
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(questions),
      })
    })

    await page.route("**/step2/match", async (route) => {
      matched = true
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ matched: 1, total: 2 }),
      })
    })

    await page.goto("/sessions/1/step2")
    await page.getByRole("button", { name: "マッチング実行" }).click()

    await expect(page.getByText("1 / 2 件がマッチ")).toBeVisible()
    await expect(page.getByRole("button", { name: "確定してStep3へ" })).toBeVisible()
  })

  test("Step2: toggle accept/reject", async ({ page }) => {
    await page.route("**/step2/results", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { question_no: 1, question_text: "セキュリティポリシーは策定されていますか？", major: "セキュリティ管理", minor: "基本方針", past_question_text: "情報セキュリティポリシーの策定状況を教えてください", past_answer_text: "当社ではセキュリティポリシーを策定し、年1回の見直しと全社員への周知を実施しています。", matched_past_qa_id: 1, answer_source: "pending" },
        ]),
      })
    })

    await page.goto("/sessions/1/step2")
    // Results are pre-loaded as matched
    await expect(page.getByText("1 / 1 件がマッチ")).toBeVisible()

    // Find the reject (X) button and click it
    const xButton = page.locator("button").filter({ has: page.locator("svg.lucide-x") })
    await xButton.click()
  })

  test("Step2: confirm and navigate to Step3", async ({ page }) => {
    await page.route("**/step2/results", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([
          { question_no: 1, question_text: "セキュリティポリシーは策定されていますか？", major: "セキュリティ管理", minor: "基本方針", past_question_text: "情報セキュリティポリシーの策定状況を教えてください", past_answer_text: "当社ではセキュリティポリシーを策定し、年1回の見直しと全社員への周知を実施しています。", matched_past_qa_id: 1, answer_source: "pending" },
        ]),
      })
    })
    await page.route("**/step2/confirm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ confirmed: 1 }),
      })
    })

    await page.goto("/sessions/1/step2")
    await expect(page.getByText("1 / 1 件がマッチ")).toBeVisible()
    await page.getByRole("button", { name: "確定してStep3へ" }).click()
    await expect(page).toHaveURL(/\/sessions\/1\/step3/)
  })

  test("Step3: shows skip when all resolved", async ({ page }) => {
    await page.route("**/step3/results", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([]),
      })
    })

    await page.goto("/sessions/1/step3")
    await expect(page.getByText("全ての質問がStep2で解決済みです")).toBeVisible()
    await expect(page.getByRole("button", { name: "Step4へスキップ" })).toBeVisible()
  })

  test("Step3: match and confirm to Step4", async ({ page }) => {
    let matched = false

    await page.route("**/step3/results", async (route) => {
      const questions = [
        { question_no: 2, question_text: "バックアップは？", matched_common_id: matched ? 1 : null, common_answer_text: matched ? "毎日バックアップ" : "", answer_source: "pending" },
      ]
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(questions),
      })
    })

    await page.route("**/step3/match", async (route) => {
      matched = true
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ matched: 1, total: 1 }),
      })
    })

    await page.route("**/step3/confirm", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ confirmed: 1 }),
      })
    })

    await page.goto("/sessions/1/step3")
    await page.getByRole("button", { name: "マッチング実行" }).click()
    await expect(page.getByText("1 / 1 件がマッチ")).toBeVisible()

    await page.getByRole("button", { name: "確定してStep4へ" }).click()
    await expect(page).toHaveURL(/\/sessions\/1\/step4/)
  })

  test("Step4: shows skip when no unresolved", async ({ page }) => {
    await page.route("**/step4/generate", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ job_id: null, message: "生成が必要な質問はありません", skipped: true }),
      })
    })

    await page.goto("/sessions/1/step4")
    await page.getByRole("button", { name: "生成を開始" }).click()
    await expect(page.getByText("生成が必要な質問はありません")).toBeVisible()
    await expect(page.getByRole("button", { name: /Step5/ })).toBeVisible()
  })

  test("Step5: shows summary stats", async ({ page }) => {
    await page.route("**/step5/summary", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session: { id: 1, bank_id: 1, status: "active", current_step: 5 },
          questions: [
            { question_no: 1, question_text: "セキュリティポリシーは策定されていますか？", major: "セキュリティ管理", minor: "基本方針", answer_source: "past_match", answer_text: "当社ではセキュリティポリシーを策定し、年1回の見直しと全社員への周知を実施しています。", source_references: [], confidence: "high", add_to_common: 0 },
            { question_no: 2, question_text: "データのバックアップ体制はどのようになっていますか？", major: "システム運用", minor: "バックアップ", answer_source: "common_match", answer_text: "日次フルバックアップを実施し、遠隔地にも複製を保管しています。RPO4時間、RTO8時間を設定しています。", source_references: [], confidence: "high", add_to_common: 0 },
          ],
          stats: { total: 2, past_match: 1, common_match: 1, generated: 0, manual: 0, pending: 0 },
        }),
      })
    })

    await page.goto("/sessions/1/step5")
    await expect(page.getByText("全2件")).toBeVisible()
    await expect(page.getByText("過去回答 1")).toBeVisible()
    await expect(page.getByText("共通回答 1")).toBeVisible()
  })

  test("Step5: edit answer", async ({ page }) => {
    await page.route("**/step5/summary", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session: { id: 1, bank_id: 1, status: "active", current_step: 5 },
          questions: [
            { question_no: 1, question_text: "テスト質問", major: "", minor: "", answer_source: "past_match", answer_text: "元の回答", source_references: [], confidence: "high", add_to_common: 0 },
          ],
          stats: { total: 1, past_match: 1, common_match: 0, generated: 0, manual: 0, pending: 0 },
        }),
      })
    })

    await page.route("**/sessions/1/questions/1", async (route) => {
      if (route.request().method() === "PUT") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify({ ok: true }),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto("/sessions/1/step5")
    await expect(page.getByText("元の回答")).toBeVisible()

    // Click edit button
    await page.getByRole("button").filter({ has: page.locator("svg.lucide-pencil") }).click()

    // Edit in dialog - target the textarea inside the dialog
    await page.getByRole("dialog").locator("textarea").fill("修正された回答")
    await page.getByRole("button", { name: "保存" }).click()
  })

  test("Step5: finalize and export", async ({ page }) => {
    let finalized = false

    await page.route("**/step5/summary", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          session: { id: 1, bank_id: 1, status: finalized ? "completed" : "active", current_step: 5 },
          questions: [
            { question_no: 1, question_text: "セキュリティポリシーは策定されていますか？", major: "セキュリティ管理", minor: "基本方針", answer_source: "past_match", answer_text: "当社ではセキュリティポリシーを策定し、年1回の見直しと全社員への周知を実施しています。", source_references: [], confidence: "high", add_to_common: 0 },
          ],
          stats: { total: 1, past_match: 1, common_match: 0, generated: 0, manual: 0, pending: 0 },
        }),
      })
    })

    await page.route("**/step5/finalize", async (route) => {
      finalized = true
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ ok: true, accumulated: 1 }),
      })
    })

    await page.goto("/sessions/1/step5")

    page.on("dialog", (d) => d.accept())
    await page.getByRole("button", { name: "確定して蓄積" }).click()

    await expect(page.getByText("確定済み")).toBeVisible()
    await expect(page.getByRole("button", { name: /エクスポート/ })).toBeVisible()
  })
})
