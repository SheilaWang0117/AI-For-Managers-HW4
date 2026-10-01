export type Stock = { size: string; quantity: number }
export type Product = {
  product_id: string
  name: string
  garment_type: string
  description: string
  colors: string[]
  search_tags: string[]
  image_url: string
  price: number
  inventory: Stock[]
}

export async function getProducts(signal?: AbortSignal): Promise<Product[]> {
  const response = await fetch('/api/products', { signal })
  if (!response.ok) throw new Error('The catalogue is taking a break. Please try again in a moment.')
  return response.json()
}

export type ProductSearchResult = {
  query: string
  max_price: number | null
  size: string | null
  in_stock_only: boolean
  total_matches: number
  products: Product[]
}
export type PageContext = { page: 'home' | 'products' | 'product' | 'about' | 'account' | 'login' | 'create-account' | 'other'; product_id?: string }
export type ChatMessage = { role: 'user' | 'assistant'; content: string; products?: Product[]; search?: ProductSearchResult | null }
export type ChatReply = { reply: string; products: Product[]; search: ProductSearchResult | null }
export class ChatError extends Error {
  constructor(message: string, public status: number) { super(message) }
}

async function chatRequest(path: string, message?: string, signal?: AbortSignal, page_context?: PageContext): Promise<Response> {
  const response = await fetch(path, {
    method: message === undefined ? 'GET' : 'POST', credentials: 'same-origin', cache: 'no-store', signal,
    headers: message === undefined ? undefined : { 'Content-Type': 'application/json', 'X-Requested-With': 'CampusCustoms' },
    body: message === undefined ? undefined : JSON.stringify({ message, page_context }),
  })
  if (!response.ok) {
    const body = await response.json().catch(() => ({}))
    throw new ChatError(typeof body.detail === 'string' ? body.detail : 'Chat is taking a break. Please try again.', response.status)
  }
  return response
}
export async function sendChatMessage(message: string, signal?: AbortSignal, pageContext?: PageContext): Promise<ChatReply> {
  return (await chatRequest('/api/chat', message, signal, pageContext)).json()
}
export async function getChatHistory(signal?: AbortSignal): Promise<ChatMessage[]> {
  return (await (await chatRequest('/api/chat/history', undefined, signal)).json()).messages
}

// The source shop uses USD; the local catalogue has no currency field.
export const money = (price: number) => new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price)

export type User = {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string
}

export type Signup = { first_name: string; last_name: string; email: string; password: string; confirm_password: string }

async function authRequest(path: string, data?: object): Promise<Response> {
  let response: Response
  try {
    response = await fetch(`/api/auth/${path}`, {
      method: data === undefined ? 'GET' : 'POST',
      credentials: 'same-origin',
      headers: data === undefined ? undefined : { 'Content-Type': 'application/json', 'X-Requested-With': 'CampusCustoms' },
      body: data === undefined ? undefined : JSON.stringify(data),
      cache: 'no-store',
    })
  } catch { throw new Error('We couldn’t reach the shop. Please try again in a moment.') }
  if (!response.ok && !(path === 'me' && response.status === 401)) {
    const body = await response.json().catch(() => ({}))
    throw new Error(typeof body.detail === 'string' ? body.detail : 'Something went wrong. Please try again.')
  }
  return response
}

export async function currentUser(): Promise<User | null> {
  const response = await authRequest('me')
  return response.status === 401 ? null : response.json()
}
export async function login(email: string, password: string): Promise<User> {
  return (await authRequest('login', { email, password })).json()
}
export async function register(data: Signup): Promise<User> {
  return (await authRequest('register', data)).json()
}
export async function logout(): Promise<void> { await authRequest('logout', {}) }
