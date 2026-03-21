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
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("当社ではセキュリティポリシーを策定し、年1回の見直しと全社員への周知を実施しています。")
    await page.getByRole("button", { name: "追加" }).click()

    // Wait for dialog to close
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: question })).toBeVisible()
  })

  test("edits a common answer", async ({ page }) => {
    const question = `編集Q${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(question)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("アクセス権限は最小権限の原則に基づき、四半期ごとに棚卸しを実施しています。")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: question })).toBeVisible()

    // Edit
    const row = page.getByRole("row").filter({ hasText: question })
    await row.getByRole("button").filter({ has: page.locator("svg.lucide-pencil") }).click()
    const newAnswer = `アクセス権限は最小権限の原則に基づき、毎月棚卸しを実施しています。${uid()}`
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill(newAnswer)
    await page.getByRole("button", { name: "更新" }).click()

    await expect(page.getByRole("dialog")).not.toBeVisible()
    await expect(page.getByRole("cell", { name: newAnswer })).toBeVisible()
  })

  test("deletes a common answer", async ({ page }) => {
    const question = `削除Q${uid()}`
    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(question)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("障害発生時にはBCP計画に基づき、2時間以内に代替システムへの切り替えを実施します。")
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
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("当社では日次でフルバックアップを実施し、遠隔地にも複製を保管しています。RPOは4時間、RTOは8時間に設定しています。")
    await page.getByRole("button", { name: "追加" }).click()
    await expect(page.getByRole("dialog")).not.toBeVisible()

    await page.getByRole("button", { name: "新規追加" }).click()
    await page.getByPlaceholder("セキュリティポリシーは策定されていますか？").fill(q2)
    await page.getByPlaceholder("当社ではセキュリティポリシーを策定しており").fill("全社員に対して多要素認証（MFA）を導入済みです。FIDO2セキュリティキーおよびTOTPアプリを認証手段として利用しています。")
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
