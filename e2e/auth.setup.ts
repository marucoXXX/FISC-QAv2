import { test as setup, expect } from "@playwright/test"
import path from "path"
import fs from "fs"

const authFile = path.join(__dirname, ".auth/user.json")

setup("authenticate", async ({ page }) => {
  // Ensure directory exists
  fs.mkdirSync(path.dirname(authFile), { recursive: true })

  await page.goto("/login")
  await page.getByLabel("メールアドレス").fill("test@example.com")
  await page.getByRole("button", { name: "ログイン" }).click()

  // Wait for redirect to /banks
  await page.waitForURL("**/banks")

  await page.context().storageState({ path: authFile })
})
