import { test, expect } from "@playwright/test"

test.describe("Navigation", () => {
  test("sidebar links navigate to correct pages", async ({ page }) => {
    await page.goto("/banks")

    // Click "共通回答DB管理" in sidebar
    await page.getByRole("link", { name: "共通回答DB管理" }).click()
    await expect(page).toHaveURL(/\/common-answers/)
    await expect(page.locator("h1")).toContainText("共通回答DB管理")

    // Click "ワークフロー" in sidebar
    await page.getByRole("link", { name: "ワークフロー", exact: true }).click()
    await expect(page).toHaveURL(/\/sessions/)
    await expect(page.locator("h1")).toContainText("ワークフロー")

    // Click "金融機関・アンケート管理" in sidebar
    await page.getByRole("link", { name: "金融機関・アンケート管理" }).click()
    await expect(page).toHaveURL(/\/banks/)
    await expect(page.locator("h1")).toContainText("金融機関・アンケート管理")
  })

  test("session row navigates to appropriate step", async ({ page }) => {
    // Mock sessions list
    await page.route("**/api/sessions", async (route) => {
      if (route.request().method() === "GET") {
        await route.fulfill({
          status: 200,
          contentType: "application/json",
          body: JSON.stringify([
            { id: 1, bank_name: "テスト銀行", name: "test.xlsx", current_step: 3, status: "active", created_at: "2026-01-01T00:00:00" },
          ]),
        })
      } else {
        await route.continue()
      }
    })

    await page.goto("/sessions")
    await page.getByRole("link", { name: "test.xlsx" }).click()
    await expect(page).toHaveURL(/\/sessions\/1\/step3/)
  })

  test("root redirects to /banks", async ({ page }) => {
    await page.goto("/")
    await expect(page).toHaveURL(/\/banks/)
  })

  test("dark mode toggle changes theme", async ({ page }) => {
    await page.goto("/banks")

    // Find and click theme toggle
    const themeBtn = page.getByRole("button", { name: "テーマを切り替え" })
    await themeBtn.click()

    // Check that html element has dark class (or theme attribute changes)
    const htmlClass = await page.locator("html").getAttribute("class")
    const hasDark = htmlClass?.includes("dark")

    // Toggle again
    await themeBtn.click()
    const htmlClass2 = await page.locator("html").getAttribute("class")
    const hasDark2 = htmlClass2?.includes("dark")

    // One should be dark, the other light
    expect(hasDark).not.toBe(hasDark2)
  })
})
