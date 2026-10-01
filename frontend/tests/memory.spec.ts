import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'

mkdirSync('../output/screenshots', { recursive: true })

// Mocked UI contracts; persistence/account authorization are tested against SQLite in Python.
test('guests can chat and each send carries the current page, never a customer identity', async ({ page }) => {
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Guest' } }))
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [] } }))
  const requests: object[] = []
  await page.route('**/api/chat', route => {
    requests.push(route.request().postDataJSON())
    return route.fulfill({ json: { reply: 'Local UI test: page context received.', products: [], search: null } })
  })
  await page.goto('/products/ua-gameday-double-knit-hood')
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const input = page.getByLabel('Message Handsome Dan')
  await expect(input).toBeEnabled()
  await expect(page.getByRole('dialog')).toContainText('Guest chat is temporary')
  await input.fill('Do you have this in pink?')
  await input.press('Enter')
  await expect(page.locator('.chat-entry.assistant')).toContainText('page context received')
  await page.screenshot({ path: '../output/screenshots/p8-guest-page-context-local.png' })
  expect(requests[0]).toEqual({ message: 'Do you have this in pink?', page_context: { page: 'product', product_id: 'ua-gameday-double-knit-hood' } })
  // Navigate with the widget still mounted; the next message must not reuse the old item.
  await page.locator('.breadcrumbs').getByRole('link', { name: 'The collection' }).click()
  await page.locator('.product-card[href="/products/champion-reverse-weave-hoodie-1"]').click()
  await input.fill('And this one?')
  await input.press('Enter')
  await expect.poll(() => requests.length).toBe(2)
  expect(requests[1]).toEqual({ message: 'And this one?', page_context: { page: 'product', product_id: 'champion-reverse-weave-hoodie-1' } })
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Home', exact: true }).click()
  await expect(input).toBeEnabled()
  await input.fill('Hello')
  await input.press('Enter')
  await expect.poll(() => requests.length).toBe(3)
  expect(requests[2]).toEqual({ message: 'Hello', page_context: { page: 'home' } })
})

test('login and logout switch history and results without merging guest messages', async ({ page }) => {
  let signedIn = false
  const user = { id: 98765, name: 'Memory Shopper', first_name: 'Memory', last_name: 'Shopper', email: 'memory@example.com', created_at: '2026-09-30' }
  await page.route('**/api/auth/me', route => route.fulfill(signedIn ? { json: user } : { status: 401, json: { detail: 'Guest' } }))
  await page.route('**/api/auth/login', route => { signedIn = true; return route.fulfill({ json: user }) })
  await page.route('**/api/auth/logout', route => { signedIn = false; return route.fulfill({ status: 204 }) })
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [
    { role: 'user', content: signedIn ? 'Saved account preference: navy.' : 'Temporary guest preference: gold.' },
    { role: 'assistant', content: signedIn ? 'Local UI test: welcome back to your saved conversation.' : 'Guest conversation.' },
  ] } }))
  await page.goto('/')
  const open = () => page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  await open()
  await expect(page.getByRole('log')).toContainText('Temporary guest preference: gold.')
  await page.getByRole('link', { name: 'Log in to save your chats ↗' }).click()
  await page.getByLabel('Email', { exact: true }).fill('memory@example.com')
  await page.getByLabel('Password', { exact: true }).fill('test-only-password')
  await page.getByRole('button', { name: 'Log in ↗' }).click()
  await expect(page).toHaveURL(/\/account$/)
  await open()
  await expect(page.getByRole('log')).toContainText('Saved account preference: navy.')
  await expect(page.getByRole('log')).not.toContainText('Temporary guest preference')
  await expect(page.getByRole('dialog')).toContainText('Chats saved to your account')
  await page.screenshot({ path: '../output/screenshots/p8-account-history-local.png' })
  await page.getByRole('button', { name: 'Close chat', exact: true }).click()
  await page.getByRole('button', { name: 'Log out', exact: true }).click()
  await open()
  await expect(page.getByRole('log')).toContainText('Temporary guest preference: gold.')
  await expect(page.getByRole('log')).not.toContainText('Saved account preference')
})
