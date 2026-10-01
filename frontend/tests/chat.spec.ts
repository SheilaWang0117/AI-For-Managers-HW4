import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import type { Product } from '../src/api'

// These UI tests stub chat responses explicitly and make no model calls.
test('chat sends the API contract, displays recommendations, and links to real items', async ({ page }) => {
  const products: Product[] = await (await page.request.get('/api/products')).json()
  const product = products.find(product => product.product_id === 'champion-reverse-weave-hoodie-1')!
  await page.route('**/api/auth/me', route => route.fulfill({ json: {
    id: 999999, name: 'Interface Test', first_name: 'Interface', last_name: 'Test', email: 'interface@example.com', created_at: '2026-09-30',
  } }))
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [] } }))
  let sent = false
  await page.route('**/api/chat', async route => {
    expect(route.request().method()).toBe('POST')
    expect(route.request().headers()['x-requested-with']).toBe('CampusCustoms')
    expect(route.request().postDataJSON()).toEqual({ message: 'Show me a navy hoodie.', page_context: { page: 'home' } })
    sent = true
    await route.fulfill({ json: { reply: 'Local interface test response: this card comes from the catalogue. This screenshot is not a live AI reply.', products: [product] } })
  })
  await page.goto('/')
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const input = page.getByLabel('Message Handsome Dan')
  await expect(input).toBeEnabled()
  await input.fill('Show me a navy hoodie.')
  await input.press('Enter')
  await expect(page.getByText(/Local interface test response/)).toBeVisible()
  expect(sent).toBeTruthy()
  await expect(page.getByRole('heading', { name: 'Picked for you.' })).toBeVisible()
  await expect(page.locator('.chat-picks .product-card')).toHaveCount(1)
  await expect(page.locator('.chat-product')).toContainText(product.name)
  mkdirSync('../output/screenshots', { recursive: true })
  await page.screenshot({ path: '../output/screenshots/p5-chat-local-interface.png' })
  await page.locator('.chat-product').click()
  await expect(page).toHaveURL(new RegExp(`/products/${product.product_id}$`))
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(product.name)
})

test('a chat failure preserves the message for retry without inventing an answer', async ({ page }) => {
  await page.route('**/api/auth/me', route => route.fulfill({ json: {
    id: 999999, name: 'Interface Test', first_name: 'Interface', last_name: 'Test', email: 'interface@example.com', created_at: '2026-09-30',
  } }))
  await page.route('**/api/chat/history', route => route.fulfill({ json: { messages: [] } }))
  await page.route('**/api/chat', route => route.fulfill({ status: 503, json: { detail: 'The AI provider is unavailable.' } }))
  await page.goto('/')
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const input = page.getByLabel('Message Handsome Dan')
  await expect(input).toBeEnabled()
  await input.fill('Find me a hoodie.')
  await input.press('Enter')
  await expect(page.getByRole('alert')).toContainText('The AI provider is unavailable.')
  await expect(input).toHaveValue('Find me a hoodie.')
  await expect(input).toBeEnabled()
  await expect(page.locator('.chat-product')).toHaveCount(0)
})
