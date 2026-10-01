import { test, expect } from '@playwright/test'
import type { Product, ProductSearchResult } from '../src/api'

// Deterministic interface tests; catalogue data is real, chat responses are mocked.
test('page searches replace matches, retain them on thanks, restore history, and open full details', async ({ page }) => {
  const products: Product[] = await (await page.request.get('/api/products')).json()
  const hoodie = products.find(p => p.product_id === 'ua-gameday-double-knit-hood')!
  const shirt = products.find(p => p.garment_type === 'short-sleeve T-shirt')!
  await page.route('**/api/auth/me', route => route.fulfill({ json: { id: 999999, name: 'UI Test', first_name: 'UI', last_name: 'Test', email: 'ui@example.com', created_at: '2026-09-30' } }))
  const history: object[] = []
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: history } }))
  const search = (query: string, products: Product[]): ProductSearchResult => ({ query, products, total_matches: products.length, max_price: null, size: null, in_stock_only: false })
  await page.route('**/api/chat', route => {
    const message = route.request().postDataJSON().message as string
    const result = message === 'hoodies' ? search(message, [hoodie]) : message === 'shirts' ? search(message, [shirt]) : message === 'spacesuits' ? search(message, []) : null
    const reply = { reply: result ? `Local test: ${message}` : 'You’re welcome!', products: result?.products ?? [], search: result }
    history.push({ role: 'user', content: message }, { role: 'assistant', content: reply.reply, products: reply.products, search: result })
    return route.fulfill({ json: reply })
  })
  await page.goto('/products')
  const open = () => page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const close = () => page.getByRole('button', { name: 'Close chat', exact: true }).click()
  const send = async (message: string) => {
    const input = page.getByLabel('Message Handsome Dan')
    await expect(input).toBeEnabled()
    await input.fill(message)
    await input.press('Enter')
    await expect(input).toBeEnabled()
  }
  await open()
  await send('hoodies')
  const shelf = page.getByRole('region', { name: 'Handsome Dan’s finds' })
  await expect(shelf.locator('.product-card')).toHaveCount(1)
  await expect(shelf.locator('.card-description')).toHaveText(hoodie.description)
  await expect(shelf.locator('.card-description')).toBeVisible()
  await close()
  await shelf.locator('.product-card').click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(hoodie.name)
  await expect(shelf).toHaveCount(0)
  await expect(page.locator('.detail-photo img')).toBeVisible()
  await expect(page.locator('.full-description')).toHaveText(hoodie.description)
  await page.getByRole('button', { name: 'M, 8 in stock', exact: true }).click()
  await expect(page.locator('.stock-message')).toHaveText('8 available in M')
  await page.goBack()
  await expect(shelf.locator('.card-title')).toContainText(hoodie.name)
  await open()
  await send('shirts')
  await expect(shelf.locator('.card-title')).toContainText(shirt.name)
  await send('thanks')
  await expect(shelf.locator('.card-title')).toContainText(shirt.name)
  await page.reload()
  await open()
  await expect(shelf.locator('.card-title')).toContainText(shirt.name)
  await send('spacesuits')
  await expect(shelf.locator('.product-card')).toHaveCount(0)
  await expect(shelf).toContainText('Showing 0 of 0 matches')
  await expect(shelf).toContainText('No matches this time, bulldog.')
  await page.reload()
  await open()
  await expect(shelf).toContainText('No matches this time, bulldog.')
})
