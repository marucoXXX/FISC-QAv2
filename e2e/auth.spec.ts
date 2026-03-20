import { test, expect } from "@playwright/test"

// Auth tests don't use storageState — they test the login flow itself
test.use({ storageState: { cookies: [], origins: [] } })

test.describe("Authentication", () => {
  test("unauthenticated user is redirected to /login", async ({ page }) => {
    await page.goto("/banks")
    await expect(page).toHaveURL(/\/login/)
  })

  test("login succeeds with valid email", async ({ page }) => {
    await page.goto("/login")
    await page.getByLabel("メールアドレス").fill("test@example.com")
    await page.getByRole("button", { name: "ログイン" }).click()

    await page.waitForURL("**/banks")
    // Verify we're on the banks page (authenticated)
    await expect(page.getByRole("columnheader", { name: "銀行名" })).toBeVisible()
  })

  test("login fails with restricted email when ALLOWED_EMAILS is set", async ({
    page,
    request,
  }) => {
    // This test only works when the backend has ALLOWED_EMAILS configured.
    // When ALLOWED_EMAILS is empty (default dev), all emails are accepted.
    // We test the frontend error display by mocking the API response.
    await page.goto("/login")

    await page.route("**/api/auth/login", async (route) => {
      await route.fulfill({
        status: 403,
        contentType: "application/json",
        body: JSON.stringify({
          detail: "このメールアドレスはログインが許可されていません",
        }),
      })
    })

    await page.getByLabel("メールアドレス").fill("unauthorized@example.com")
    await page.getByRole("button", { name: "ログイン" }).click()

    await expect(
      page.getByText("このメールアドレスはログインが許可されていません")
    ).toBeVisible()
  })

  test("logout returns to /login", async ({ page }) => {
    // First login
    await page.goto("/login")
    await page.getByLabel("メールアドレス").fill("test@example.com")
    await page.getByRole("button", { name: "ログイン" }).click()
    await page.waitForURL("**/banks")

    // Click logout in sidebar
    await page.getByRole("button", { name: /test/ }).click()
    await expect(page).toHaveURL(/\/login/)
  })
})
