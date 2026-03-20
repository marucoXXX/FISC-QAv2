import { test, expect } from "@playwright/test"

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 5)

test.describe("Bank Management", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/banks")
  })

  test("shows table headers on initial load", async ({ page }) => {
    await expect(page.getByRole("columnheader", { name: "銀行名" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "コード" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "形式" })).toBeVisible()
  })

  test("creates a new bank", async ({ page }) => {
    const name = `作成銀行${uid()}`
    const code = `crt-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name })).toBeVisible()
  })

  test("shows error on duplicate code", async ({ page }) => {
    const code = `dup-${uid()}`
    const nameA = `DupTestA${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(nameA)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()

    // Wait for dialog to close and list to update
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: nameA })).toBeVisible()

    // Try same code
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill("銀行B")
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()

    await expect(page.getByText("重複しています")).toBeVisible()
  })

  test("edits a bank", async ({ page }) => {
    const name = `編集前${uid()}`
    const code = `edt-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name })).toBeVisible()

    // Edit
    const row = page.getByRole("row").filter({ hasText: name })
    await row.getByRole("button").filter({ has: page.locator("svg.lucide-pencil") }).click()
    const newName = `編集後${uid()}`
    await page.getByPlaceholder("みずほ銀行").fill(newName)
    await page.getByRole("button", { name: "更新" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: newName })).toBeVisible()
    await expect(page.getByRole("cell", { name })).not.toBeVisible()
  })

  test("deletes a bank", async ({ page }) => {
    const name = `削除銀行${uid()}`
    const code = `del-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name })).toBeVisible()

    page.on("dialog", (d) => d.accept())
    const row = page.getByRole("row").filter({ hasText: name })
    await row.getByRole("button").filter({ has: page.locator("svg.lucide-trash-2") }).click()

    await expect(page.getByRole("cell", { name })).not.toBeVisible()
  })

  test("navigates to bank detail", async ({ page }) => {
    const name = `詳細銀行${uid()}`
    const code = `dtl-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    await page.getByRole("link", { name }).click()
    await expect(page).toHaveURL(/\/banks\/\d+/)
  })

  test("shows format settings on detail page", async ({ page }) => {
    const name = `FMT銀行${uid()}`
    const code = `fmt-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    await page.getByRole("link", { name }).click()
    await expect(page).toHaveURL(/\/banks\/\d+/)
    await expect(page.getByText("フォーマット設定", { exact: true })).toBeVisible()
    await expect(page.getByText("XLSX")).toBeVisible()
  })

  test("uploads past answers file", async ({ page }) => {
    const name = `UPL銀行${uid()}`
    const code = `upl-${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("みずほ銀行").fill(name)
    await page.getByPlaceholder("mizuho").fill(code)
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    await page.getByRole("link", { name }).click()
    await expect(page).toHaveURL(/\/banks\/\d+/)

    await page.route("**/past-answers/upload", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ count: 3, message: "3件のQ&Aペアを登録しました" }),
      })
    })

    let uploaded = false
    await page.route("**/past-answers", async (route) => {
      if (route.request().method() === "GET" && uploaded) {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, bank_id: 1, question_text: "Q1", answer_text: "A1", source_file: "test.xlsx", created_at: "2026-01-01" },
            { id: 2, bank_id: 1, question_text: "Q2", answer_text: "A2", source_file: "test.xlsx", created_at: "2026-01-01" },
            { id: 3, bank_id: 1, question_text: "Q3", answer_text: "A3", source_file: "test.xlsx", created_at: "2026-01-01" },
          ]),
        })
      } else {
        await route.continue()
      }
    })

    const fileInput = page.locator('input[type="file"]')
    uploaded = true
    await fileInput.setInputFiles({
      name: "test.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("fake-xlsx-content"),
    })

    await expect(page.getByText("3件のQ&Aペアを登録しました")).toBeVisible()
  })
})
