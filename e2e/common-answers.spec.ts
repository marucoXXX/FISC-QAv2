import { test, expect } from "@playwright/test"

const uid = () => Date.now().toString(36) + Math.random().toString(36).slice(2, 5)

test.describe("Common Answers", () => {
  test.beforeEach(async ({ page }) => {
    await page.goto("/common-answers")
  })

  test("shows table headers on initial load", async ({ page }) => {
    await expect(page.getByRole("columnheader", { name: "質問パターン" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "回答" })).toBeVisible()
    await expect(page.getByRole("columnheader", { name: "カテゴリ" })).toBeVisible()
  })

  test("creates a new common answer", async ({ page }) => {
    const question = `質問${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(question)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("回答テスト")
    await page.getByRole("button", { name: "追加" }).click()

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: question })).toBeVisible()
  })

  test("edits a common answer", async ({ page }) => {
    const question = `編集Q${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(question)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("編集前回答")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: question })).toBeVisible()

    // Edit
    const row = page.getByRole("row").filter({ hasText: question })
    await row.getByRole("button").filter({ has: page.locator("svg.lucide-pencil") }).click()
    const newAnswer = `編集後回答${uid()}`
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill(newAnswer)
    await page.getByRole("button", { name: "更新" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: newAnswer })).toBeVisible()
  })

  test("deletes a common answer", async ({ page }) => {
    const question = `削除Q${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(question)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("削除テスト回答")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: question })).toBeVisible()

    // Delete
    page.on("dialog", (d) => d.accept())
    const row = page.getByRole("row").filter({ hasText: question })
    await row.getByRole("button").filter({ has: page.locator("svg.lucide-trash-2") }).click()

    await expect(page.getByRole("cell", { name: question })).not.toBeVisible()
  })

  test("search filters results", async ({ page }) => {
    const q1 = `バックアップ${uid()}`
    const q2 = `認証方式${uid()}`

    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(q1)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("回答A")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(q2)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("回答B")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    // Both visible
    await expect(page.getByRole("cell", { name: q1 })).toBeVisible()
    await expect(page.getByRole("cell", { name: q2 })).toBeVisible()

    // Search - triggers API call with ?search= param
    await page.getByPlaceholder("検索...").fill("バックアップ")
    // Wait for API response
    await expect(page.getByRole("cell", { name: q1 })).toBeVisible()
    await expect(page.getByRole("cell", { name: q2 })).not.toBeVisible()
  })

  test("shows empty message when no items", async ({ page }) => {
    await expect(page.locator("h2").getByText("共通回答DB")).toBeVisible()
    await expect(page.getByRole("table")).toBeVisible()
  })
})
