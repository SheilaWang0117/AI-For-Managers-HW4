import { test, expect } from '@playwright/test'
import { mkdirSync } from 'node:fs'
import type { Product } from '../src/api'

const screenshots = '../output/screenshots'
mkdirSync(screenshots, { recursive: true })

test('catalogue API supplies real images and stock and does not expose the database', async ({ request }) => {
  const response = await request.get('/api/products')
  expect(response.ok()).toBeTruthy()
  const products: Product[] = await response.json()
  expect(products).toHaveLength(102)
  for (const product of products) {
    expect(product.inventory).toHaveLength(6)
    const image = await request.get(product.image_url)
    expect(image.ok(), product.image_url).toBeTruthy()
    expect(image.headers()['content-type']).toMatch(/^image\//)
  }
  const detail = await request.get(`/api/products/${products[0].product_id}`)
  expect(await detail.json()).toEqual(products[0])
  expect((await request.get('/api/products/not-a-real-product')).status()).toBe(404)
  expect((await request.get('/api/products/%27%20OR%201%3D1--')).status()).toBe(404)
  expect((await request.get('/api/images/campus_customs.db')).status()).toBe(404)
  expect((await request.get('/api/images/%2e%2e%2fcampus_customs.db')).status()).toBe(404)
})

test('home, search, product links, and size stock work together', async ({ page }) => {
  const errors: string[] = []
  page.on('pageerror', error => errors.push(error.message))
  await page.goto('/')
  await expect(page.locator('.featured .product-card')).toHaveCount(3)
  await page.screenshot({ path: `${screenshots}/p3-home-desktop.png`, fullPage: true })
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'Products', exact: true }).click()
  await expect(page.locator('.product-card')).toHaveCount(102)
  await page.getByLabel('Search the collection').fill('hoodie')
  await expect(page.locator('.product-card').first()).toBeVisible()
  await expect.poll(() => page.locator('.product-card').count()).toBeLessThan(102)
  await page.getByLabel('Search the collection').fill('no-matching-bulldog-xyz')
  await expect(page.getByText('No matches just yet.')).toBeVisible()
  await page.getByRole('button', { name: 'Reset filters' }).click()
  await expect(page.locator('.product-card')).toHaveCount(102)
  await page.screenshot({ path: `${screenshots}/p3-products-desktop.png` })
  const products: Product[] = await (await page.request.get('/api/products')).json()
  const product = products.find(p => p.inventory.some(s => s.quantity === 0) && p.inventory.some(s => s.quantity > 0))!
  await page.locator(`.product-card[href="/products/${product.product_id}"]`).click()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(product.name)
  await expect(page.locator('.full-description')).toHaveText(product.description)
  const available = product.inventory.find(s => s.quantity > 0)!
  await page.getByRole('button', { name: `${available.size}, ${available.quantity} in stock`, exact: true }).click()
  await expect(page.locator('.stock-message')).toHaveText(`${available.quantity} available in ${available.size}`)
  const soldOut = product.inventory.find(s => s.quantity === 0)!
  await page.getByRole('button', { name: `${soldOut.size}, sold out`, exact: true }).click()
  await expect(page.locator('.stock-message')).toHaveText(`${soldOut.size} is currently sold out`)
  await page.screenshot({ path: `${screenshots}/p3-product-detail.png`, fullPage: true })
  await page.reload()
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(product.name)
  expect(errors).toEqual([])
})

test('filters and price sorting are usable', async ({ page }) => {
  await page.goto('/products')
  await expect(page.locator('.product-card')).toHaveCount(102)
  await page.getByRole('combobox', { name: 'Category', exact: true }).selectOption({ label: 'short-sleeve T-shirt' })
  await expect(page).toHaveURL(/category=short-sleeve/)
  await expect.poll(async () => (await page.locator('.card-category').allTextContents()).every(value => value === 'short-sleeve T-shirt')).toBeTruthy()
  const categories = await page.locator('.card-category').allTextContents()
  expect(categories.length).toBeGreaterThan(0)
  expect(categories.every(value => value === 'short-sleeve T-shirt')).toBeTruthy()
  await page.getByRole('combobox', { name: 'Sort by' }).selectOption('high')
  await expect(page).toHaveURL(/sort=high/)
  const prices = (await page.locator('.card-title > span').allTextContents()).map(text => Number(text.replace('$', '')))
  expect(prices).toEqual([...prices].sort((a, b) => b - a))
})

test('mobile navigation and temporary guest chat remain usable', async ({ page }) => {
  await page.setViewportSize({ width: 390, height: 844 })
  await page.goto('/')
  await expect(page.locator('.featured .product-card').first()).toBeVisible()
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy()
  await page.screenshot({ path: `${screenshots}/p3-home-mobile.png`, fullPage: true })
  await page.getByRole('button', { name: 'Chat with Handsome Dan' }).click()
  const dialog = page.getByRole('dialog')
  await expect(dialog).toBeVisible()
  await expect(page.getByLabel('Message Handsome Dan')).toBeEnabled()
  await expect(dialog.getByRole('link', { name: 'Log in to save your chats ↗' })).toBeVisible()
  await page.screenshot({ path: `${screenshots}/p5-chat-guest-mobile.png` })
  await dialog.getByRole('button', { name: 'Close chat' }).press('Escape')
  await expect(dialog).toHaveCount(0)
  await expect(page.locator('.chat-launcher')).toBeFocused()
  await page.getByRole('navigation', { name: 'Main navigation' }).getByRole('link', { name: 'About us' }).click()
  await expect(page.getByRole('heading', { level: 1 })).toContainText('Belonging travels.')
  await page.locator('.account-nav').getByRole('link', { name: 'Log in' }).click()
  await expect(page.getByRole('button', { name: 'Log in ↗' })).toBeEnabled()
  await page.getByRole('link', { name: 'Create account', exact: true }).first().click()
  await expect(page.getByRole('button', { name: 'Create account ↗' })).toBeEnabled()
})

test('network errors, retry, and unknown routes are handled honestly', async ({ page }) => {
  await page.route('**/api/products', route => route.fulfill({ status: 503, body: 'Unavailable' }))
  await page.goto('/products')
  await expect(page.getByRole('alert')).toBeVisible()
  await page.unroute('**/api/products')
  await page.getByRole('button', { name: 'Try again' }).click()
  await expect(page.locator('.product-card')).toHaveCount(102)
  await page.goto('/products/not-a-real-product')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('This one wandered off.')
  await page.goto('/not-a-page')
  await expect(page.getByRole('heading', { level: 1 })).toHaveText('This one wandered off.')
})
