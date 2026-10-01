import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'

mkdirSync('../output/screenshots', { recursive: true })

test('starters are editable, never auto-send, follow the page and protect a draft', async ({ page }) => {
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Guest' } }))
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [] } }))
  const sent: object[] = []
  await page.route('**/api/chat', route => {
    sent.push(route.request().postDataJSON())
    return route.fulfill({ json: { reply: 'Local UI test: **$45.00**.\n\n- **M:** 8 available\n- **L:** Sold out', products: [], search: null } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const starter = page.getByRole('button', { name: 'Hoodies under $70', exact: true })
  await expect(starter).toBeEnabled()
  await starter.focus()
  await starter.press('Enter')
  const input = page.getByLabel('Message Handsome Dan')
  await expect(input).toBeFocused()
  await expect(input).toHaveValue('Show me hoodies under $70.')
  expect(sent).toEqual([])
  await expect(page.getByRole('button', { name: 'Gifts under $50' })).toBeDisabled()
  await input.fill('Show me hoodies under $60.')
  await input.press('Enter')
  await expect(page.locator('.chat-text strong').first()).toHaveText('$45.00')
  expect(sent[0]).toEqual({ message: 'Show me hoodies under $60.', page_context: { page: 'home' } })
  await page.getByRole('button', { name: 'Close chat', exact: true }).click()
  await page.locator('.hero-product').click()
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  await expect(page.getByRole('button', { name: 'Price + size stock', exact: true })).toBeEnabled()
  await expect(starter).toHaveCount(0)
  await page.getByRole('button', { name: 'Similar items in M', exact: true }).click()
  await expect(input).toHaveValue('Find similar items in medium that are in stock.')
  await page.setViewportSize({ width: 390, height: 844 })
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await input.scrollIntoViewIfNeeded()
  await expect(input).toBeVisible()
  await page.screenshot({ path: '../output/screenshots/p9-starters-mobile-local.png' })
})

test('assistant formatting is readable while HTML, links and shopper markup stay inert', async ({ page }) => {
  await page.route('**/api/auth/me', route => route.fulfill({ status: 401, json: { detail: 'Guest' } }))
  const answer = '**Price:** $45.00\n\n- **M:** 8 available\n- **L:** Sold out\n\n1. Choose a size\n2. Open the item\n\n<img src=x onerror="window.injected=true">\n[Bad link](javascript:alert(1))\n\n- \n**unfinished'
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [
    { role: 'user', content: 'Please explain **this item**.' },
    { role: 'assistant', content: answer },
  ] } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const text = page.locator('.chat-text')
  await expect(text.locator('strong').first()).toHaveText('Price:')
  await expect(text.locator('ul li')).toHaveCount(2)
  await expect(text.locator('ol li')).toHaveCount(2)
  await expect(text).toContainText('<img src=x onerror="window.injected=true">')
  await expect(text.locator('img, script, a')).toHaveCount(0)
  expect(await page.evaluate(() => 'injected' in window)).toBeFalsy()
  await expect(page.locator('.chat-bubble.user')).toHaveText('Please explain **this item**.')
  await expect(page.getByLabel('Message Handsome Dan')).toBeEnabled()
})
