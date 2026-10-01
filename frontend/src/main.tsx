import React, { useCallback, useEffect, useRef, useState } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter, Link, Navigate, NavLink, Route, Routes, useLocation, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { ChatError, getChatHistory, getProducts, money, sendChatMessage, type ChatMessage, type PageContext, type ProductSearchResult, type Product } from './api'
import { AuthProvider, useAuth } from './auth'
import { ChatText } from './ChatText'
import './styles.css'
import './design.css'

function Bulldog({ large = false }: { large?: boolean }) {
  return <span className={`dog ${large ? 'dog-large' : ''}`} aria-hidden="true"><i className="ear left" /><i className="ear right" /><i className="dog-face"><b className="eye left" /><b className="eye right" /><i className="muzzle"><b className="nose" /><b className="mouth" /></i></i><i className="collar">Y</i></span>
}

function ProductImage({ product }: { product: Product }) {
  const [failed, setFailed] = useState(false)
  return failed ? <div className="missing-image">Photo unavailable</div> : <img src={product.image_url} alt={product.name} loading="lazy" onError={() => setFailed(true)} />
}

function ProductCard({ product }: { product: Product }) {
  const available = product.inventory.some(stock => stock.quantity > 0)
  return <Link className="product-card" to={`/products/${encodeURIComponent(product.product_id)}`}>
    <div className="product-photo"><ProductImage product={product} /><span className="photo-arrow" aria-hidden="true">↗</span>{!available && <span className="sold-out">{product.inventory.length ? 'Sold out' : 'Stock unavailable'}</span>}</div>
    <div className="card-category">{product.garment_type}</div>
    <div className="card-title"><h3>{product.name}</h3><span>{money(product.price)}</span></div>
    <p className="card-description">{product.description}</p>
    <div className="card-footnote"><span>{product.colors.join(' / ')}</span><span className="card-discover" aria-hidden="true">Take a closer look ↗</span></div>
  </Link>
}

function CatalogueStatus({ loading, error, retry }: { loading: boolean; error: string; retry: () => void }) {
  if (loading) return <div className="status" role="status">Unpacking the campus classics…</div>
  if (error) return <div className="status" role="alert"><p>{error}</p><button className="button" onClick={retry}>Try again</button></div>
  return null
}

function Home({ products }: { products: Product[] }) {
  const hero = products.find(p => p.product_id === 'champion-reverse-weave-hoodie-1') ?? products[0]
  const featured = ['champion-reverse-weave-hoodie-1', 'champion-reverse-weave-crewneck', '2025-yale-vs-harvard-t-shirt'].map(id => products.find(p => p.product_id === id)).filter((p): p is Product => !!p)
  return <>
    <div className="edition-line page-width"><span>THE CAMPUS CUSTOMS FIELD NOTES</span><span>NEW HAVEN, CT <i aria-hidden="true">✦</i> EVERYDAY CAMPUS WEAR</span></div>
    <section className="hero page-width">
      <div className="hero-copy"><p className="eyebrow">NEW HAVEN SPIRIT. EVERYDAY FAVORITES.</p><h1>A little more<br /><em>Yale.</em> A lot<br />more you.</h1><p>For early classes, late library nights, and Saturdays in the stands. Find the campus classics that feel like your kind of blue.</p><Link className="button" to="/products">Find your campus classic <span>↗</span></Link><div className="hero-note"><span className="tiny-star">✦</span> For students, alumni & the whole bulldog family</div></div>
      <div className="hero-art"><div className="hero-label">THE CAMPUS UNIFORM <span>No. 01</span></div><div className="hero-ring" /><span className="hero-word" aria-hidden="true">YALE</span>{hero && <Link className="hero-product" to={`/products/${hero.product_id}`}><ProductImage product={hero} /><span>{hero.name} <strong>{money(hero.price)} ↗</strong></span></Link>}<div className="spirit-seal">A LITTLE<br /><strong>BULLDOG</strong><br />SPIRIT ✦</div><span className="art-caption">NEW HAVEN ROOTS. EVERYWHERE ENERGY.</span></div>
    </section>
    <div className="ribbon"><span>Made for campus days</span><span>✦</span><span>Big Yale energy</span><span>✦</span><span>Your next favorite layer</span><span>✦</span><span>Always a bulldog</span></div>
    <section className="page-width section"><div className="section-heading"><div><p className="eyebrow">YOUR BLUE STARTS HERE</p><h2>Meet the campus classics.</h2></div><Link className="text-link" to="/products">Shop all products ↗</Link></div><div className="product-grid featured">{featured.map(p => <ProductCard key={p.product_id} product={p} />)}</div></section>
    <CampusMoments products={products} />
    <section className="community page-width"><div className="community-dog"><Bulldog large /></div><div><p className="eyebrow">MORE THAN A COLOR</p><h2>A place in the pack.</h2><p>First semester or fiftieth reunion, there’s something special about wearing a little piece of campus. We’re here for the everyday moments that keep you connected.</p><Link className="text-link" to="/about">Get to know Campus Customs ↗</Link></div></section>
  </>
}

function CampusMoments({ products }: { products: Product[] }) {
  const moments = [
    { number: '01', title: 'The 9 a.m. layer.', note: 'An extra layer for the walk across campus.', query: 'hoodie', id: 'champion-reverse-weave-hoodie-1', label: 'Shop hoodies' },
    { number: '02', title: 'Library, then coffee.', note: 'Easy crewnecks for your everyday rotation.', query: 'crewneck', id: 'champion-reverse-weave-crewneck', label: 'Shop crewnecks' },
    { number: '03', title: 'Meet in the stands.', note: 'Wear a little more team spirit.', query: 'football', id: '2025-yale-vs-harvard-t-shirt', label: 'Shop game-day gear' },
  ]
  return <section className="campus-moments page-width section" aria-label="Shop by campus moment">
    <div className="section-heading"><div><p className="eyebrow">THERE’S A LITTLE YALE IN EVERY DAY</p><h2>What’s on your agenda?</h2></div><p className="moment-heading-note">Three ways to wear your blue.<br /><em>Make one your own.</em></p></div>
    <div className="moment-grid">{moments.map(moment => {
      const product = products.find(item => item.product_id === moment.id)
      return <Link className="moment-card" key={moment.number} to={`/products?q=${moment.query}`} aria-label={moment.label}>
        <div className="moment-top"><span>FIELD NOTE / {moment.number}</span><span aria-hidden="true">↗</span></div>
        <div className="moment-art"><span className="moment-number" aria-hidden="true">{moment.number}</span>{product && <ProductImage product={product} />}</div>
        <div className="moment-copy"><h3>{moment.title}</h3><p>{moment.note}</p><span>{moment.label} <span aria-hidden="true">↗</span></span></div>
      </Link>
    })}</div>
  </section>
}

function Products({ products }: { products: Product[] }) {
  const [params, setParams] = useSearchParams()
  const query = params.get('q') ?? ''
  const category = params.get('category') ?? 'all'
  const sort = params.get('sort') ?? 'name'
  const categories = [...new Set(products.map(p => p.garment_type))].sort()
  function update(key: string, value: string) { const next = new URLSearchParams(params); if (value) next.set(key, value); else next.delete(key); setParams(next, { replace: true }) }
  const filtered = products.filter(p => (category === 'all' || p.garment_type === category) && `${p.name} ${p.description} ${p.colors.join(' ')} ${p.search_tags.join(' ')}`.toLowerCase().includes(query.trim().toLowerCase())).sort((a, b) => sort === 'low' ? a.price - b.price : sort === 'high' ? b.price - a.price : a.name.localeCompare(b.name))
  return <section className="page-width section"><p className="eyebrow">THE CAMPUS COLLECTION</p><h1 className="page-title">Find your kind of blue.</h1><p className="page-intro">A favorite for every day, a little spirit for every occasion.</p><div className="filters"><label className="search-field">Search the collection<input type="search" placeholder="Try navy, hoodie, football…" value={query} onChange={e => update('q', e.target.value)} /></label><label>Category<select value={category} onChange={e => update('category', e.target.value)}><option value="all">All campus gear</option>{categories.map(c => <option key={c}>{c}</option>)}</select></label><label>Sort by<select value={sort} onChange={e => update('sort', e.target.value)}><option value="name">Name: A–Z</option><option value="low">Price: low to high</option><option value="high">Price: high to low</option></select></label></div><p className="results-count" role="status">{filtered.length} {filtered.length === 1 ? 'campus classic' : 'campus classics'}</p><div className="product-grid">{filtered.map(p => <ProductCard product={p} key={p.product_id} />)}</div>{!filtered.length && <div className="status"><h2>No matches just yet.</h2><p>Try a broader search or another category.</p><button className="button" onClick={() => setParams({})}>Reset filters</button></div>}</section>
}

function ProductDetail({ products, loading, error }: { products: Product[]; loading: boolean; error: string }) {
  const { id } = useParams()
  const product = products.find(p => p.product_id === id)
  const [selected, setSelected] = useState('')
  useEffect(() => setSelected(''), [id])
  if (loading || error) return null
  if (!product) return <NotFound />
  const stock = product.inventory.find(s => s.size === selected)
  const related = products.filter(p => p.product_id !== id && p.garment_type === product.garment_type).slice(0, 3)
  return <section className="page-width section"><nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/products">The collection</Link><span>/</span><span>{product.name}</span></nav><div className="detail-layout"><div className="detail-photo"><span className="photo-edition">CAMPUS CUSTOMS / THE COLLECTION</span><ProductImage product={product} /><span className="photo-inscription" aria-hidden="true">A little piece of campus.</span></div><div className="detail-copy"><p className="eyebrow">{product.garment_type}</p><h1>{product.name}</h1><p className="detail-price">{money(product.price)} <span>USD</span></p><p className="full-description">{product.description}</p><div className="color-list"><strong>Colors</strong><span>{product.colors.join(' · ')}</span></div><fieldset className="size-field"><legend>Pick your size</legend><div className="sizes">{product.inventory.map(s => <button key={s.size} className={`${selected === s.size ? 'selected' : ''} ${s.quantity === 0 ? 'unavailable' : ''}`} aria-pressed={selected === s.size} aria-label={`${s.size}, ${s.quantity > 0 ? `${s.quantity} in stock` : 'sold out'}`} onClick={() => setSelected(s.size)}>{s.size}{s.quantity === 0 && <small>Sold out</small>}</button>)}</div></fieldset><p className={`stock-message ${stock?.quantity === 0 ? 'out' : ''}`} aria-live="polite">{stock ? stock.quantity > 0 ? `${stock.quantity} available in ${stock.size}` : `${stock.size} is currently sold out` : product.inventory.length ? 'Select a size to check its stock.' : 'Size availability is not recorded for this item.'}</p><div className="detail-note"><span>✦</span><p>Find your fit, then make it yours.<br /><small>Browsing preview · checkout is not available yet.</small></p></div><details><summary>All sizes & recorded stock</summary><table className="stock-table"><thead><tr><th>Size</th><th>Available</th></tr></thead><tbody>{product.inventory.map(s => <tr key={s.size}><td>{s.size}</td><td>{s.quantity === 0 ? 'Sold out' : s.quantity}</td></tr>)}</tbody></table><p className="muted">Stock reflects the catalogue when this page loaded.</p></details></div></div>{related.length > 0 && <div className="section"><div className="section-heading"><h2>More your style.</h2><Link className="text-link" to="/products">Explore the collection ↗</Link></div><div className="product-grid featured">{related.map(p => <ProductCard key={p.product_id} product={p} />)}</div></div>}</section>
}

function About() {
  return <section className="page-width section about"><p className="eyebrow">HELLO FROM NEW HAVEN</p><h1 className="page-title">Campus is a place.<br /><em>Belonging travels.</em></h1><div className="about-layout"><div className="about-art"><Bulldog large /><span>ROOTED IN NEW HAVEN<br />WORN EVERYWHERE</span></div><div><h2>For every kind of bulldog.</h2><p>A sweatshirt can hold a whole chapter: the walk to your first class, a chilly game day, a trip back to the place that started it all. Campus Customs is about keeping that connection close.</p><p>Inspired by Yale Bulldog Blue’s mix of campus apparel, team spirit, and gifts for the wider Yale family, our collection brings a little New Haven into your everyday rotation. Students, proud parents, longtime alumni—there’s room for everyone in the pack.</p><div className="visit-note"><p className="eyebrow">THE REAL CAMPUS CUSTOMS SHOP</p><h3>57 Broadway, New Haven, CT</h3><p>Explore the original shop for current store information and the full official collection.</p><a className="text-link" href="https://yalebulldogblue.com" target="_blank" rel="noreferrer">Visit Yale Bulldog Blue ↗</a></div><p className="muted">This storefront is a student project inspired by Campus Customs.</p></div></div></section>
}

function PasswordField({ label, name, create = false }: { label: string; name: string; create?: boolean }) {
  const [visible, setVisible] = useState(false)
  return <div className="password-field"><label htmlFor={name}>{label}</label><span className="password-input"><input id={name} name={name} type={visible ? 'text' : 'password'} autoComplete={create ? 'new-password' : 'current-password'} required minLength={create ? 12 : 1} maxLength={128} placeholder={create ? 'At least 12 characters' : 'Your password'} aria-describedby={create ? 'password-hint' : undefined} /><button type="button" onClick={() => setVisible(v => !v)} aria-label={`${visible ? 'Hide' : 'Show'} ${label.toLowerCase()}`}>{visible ? 'Hide' : 'Show'}</button></span></div>
}

function Account({ create = false }: { create?: boolean }) {
  const auth = useAuth()
  const navigate = useNavigate()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (busy) return
    setError('')
    const values = new FormData(event.currentTarget)
    const email = String(values.get('email') ?? '').trim()
    const password = String(values.get('password') ?? '')
    if (create && password !== values.get('confirm_password')) { setError('Those passwords don’t match. Give them another look.'); return }
    const firstName = String(values.get('first_name') ?? '').trim()
    const lastName = String(values.get('last_name') ?? '').trim()
    if (create && (!firstName || !lastName)) { setError('Please add your first and last name.'); return }
    setBusy(true)
    try {
      if (create) await auth.signUp({ first_name: firstName, last_name: lastName, email, password, confirm_password: String(values.get('confirm_password')) })
      else await auth.signIn(email, password)
      navigate('/account', { replace: true, state: { joined: create } })
    } catch (e) { setError(e instanceof Error ? e.message : 'Please try again.') }
    finally { setBusy(false) }
  }
  if (!auth.loading && auth.user) return <Navigate to="/account" replace />
  return <section className="account-wrap page-width"><div className="account-story"><Bulldog large /><p className="eyebrow">YOU BELONG IN BLUE</p><h1>{create ? 'Join the pack.' : 'Good to see you.'}</h1><p>{create ? 'A little campus spirit. A place to call yours.' : 'Your campus favorites are waiting for you.'}</p><span className="account-paw" aria-hidden="true">✦ &nbsp; BULLDOGS STICK TOGETHER &nbsp; ✦</span></div><div className="account-card"><p className="eyebrow">{create ? 'MAKE YOURSELF AT HOME' : 'WELCOME BACK, BULLDOG'}</p><h2>{create ? 'Create your account' : 'Welcome back'}</h2><p>{create ? 'Tell us a little about yourself and you’re in.' : 'A quick hello, and you’re back in the pack.'}</p><form onSubmit={submit} aria-busy={busy}><fieldset disabled={busy || auth.loading}>{create && <div className="name-fields"><label>First name<input name="first_name" autoComplete="given-name" required maxLength={80} placeholder="First name" /></label><label>Last name<input name="last_name" autoComplete="family-name" required maxLength={80} placeholder="Last name" /></label></div>}<label>Email<input name="email" type="email" autoComplete="email" required maxLength={254} placeholder="you@example.com" /></label><PasswordField label="Password" name="password" create={create} />{create && <><p className="password-hint" id="password-hint">Use 12–128 characters. A few unrelated words make a great passphrase.</p><PasswordField label="Confirm password" name="confirm_password" create /></>}{error && <p className="form-error" role="alert">{error}</p>}<button className="button" type="submit">{busy ? 'One moment…' : create ? 'Create account ↗' : 'Log in ↗'}</button></fieldset></form><p className="account-security">{create ? 'Your password is hashed securely. We never store it as plain text.' : 'Your account. Your little corner of campus.'}</p><p className="account-switch">{create ? 'Already part of the pack?' : 'New around here?'} <Link to={create ? '/login' : '/create-account'}>{create ? 'Log in' : 'Create account'}</Link></p></div></section>
}

function AccountHome() {
  const auth = useAuth()
  const location = useLocation()
  const navigate = useNavigate()
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  async function signOut() {
    setBusy(true); setError('')
    try { await auth.signOut(); navigate('/login', { replace: true }) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not log out. Please try again.') }
    finally { setBusy(false) }
  }
  if (auth.loading) return <div className="status" role="status">Finding your place in the pack…</div>
  if (auth.error) return <div className="status" role="alert"><p>{auth.error}</p><button className="button" onClick={() => void auth.refresh()}>Try again</button></div>
  if (!auth.user) return <Navigate to="/login" replace />
  return <section className="page-width member-page"><div className="member-welcome"><Bulldog large /><p className="eyebrow">OFFICIALLY PART OF THE PACK</p><h1>{location.state?.joined ? 'Welcome to the pack,' : 'Welcome back,'}<br /><em>{auth.user.first_name || auth.user.name}.</em></h1><p>Your next campus classic is just around the corner.</p><Link className="button" to="/products">Explore the collection ↗</Link></div><div className="member-details"><p className="eyebrow">YOUR CAMPUS CORNER</p><h2>Account details</h2><dl><dt>Name</dt><dd>{auth.user.name}</dd><dt>Email</dt><dd>{auth.user.email}</dd></dl><p className="muted">You’re signed in on this browser.</p>{error && <p className="form-error" role="alert">{error}</p>}<button className="logout-button" onClick={signOut} disabled={busy}>{busy ? 'Logging out…' : 'Log out'}</button></div></section>
}

function NotFound() { return <section className="page-width status"><Bulldog /><h1>This one wandered off.</h1><p>We couldn’t find that page or product.</p><Link className="button" to="/products">Back to the collection</Link></section> }

type ChatFinds = { products?: Product[]; search?: ProductSearchResult | null }

function pageContextFor(pathname: string): PageContext {
  const detail = pathname.match(/^\/products\/([^/]+)\/?$/)
  if (detail) {
    try { return { page: 'product', product_id: decodeURIComponent(detail[1]) } }
    catch { return { page: 'other' } }
  }
  const page = pathname.replace(/^\/|\/$/g, '')
  return { page: page === '' ? 'home' : ['products', 'about', 'account', 'login', 'create-account'].includes(page) ? page as PageContext['page'] : 'other' }
}

function Chat({ onResults }: { onResults: (result: ChatFinds) => void }) {
  const auth = useAuth()
  const location = useLocation()
  const pageContext = pageContextFor(location.pathname)
  const suggestions = pageContext.page === 'product' ? [
    { label: 'Price + size stock', message: 'What is the price of this item and which sizes are in stock?' },
    { label: 'Colors for this item', message: 'What colors are listed for this item?' },
    { label: 'Similar items in M', message: 'Find similar items in medium that are in stock.' },
  ] : [
    { label: 'Hoodies under $70', message: 'Show me hoodies under $70.' },
    { label: 'Gifts under $50', message: 'Show me campus apparel gift ideas under $50.' },
    { label: 'In stock in M', message: 'Show me campus apparel with medium in stock.' },
  ]
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState('')
  const [sending, setSending] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const [historyAttempt, setHistoryAttempt] = useState(0)
  const [error, setError] = useState('')
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const input = useRef<HTMLInputElement>(null)
  const launcher = useRef<HTMLButtonElement>(null)
  const end = useRef<HTMLDivElement>(null)
  const sendingController = useRef<AbortController | null>(null)
  useEffect(() => () => sendingController.current?.abort(), [])
  useEffect(() => { if (open && historyLoaded) input.current?.focus() }, [open, historyLoaded])
  useEffect(() => { if (open) end.current?.scrollIntoView({ block: 'nearest' }) }, [messages, open, sending])
  useEffect(() => {
    if (!open || auth.loading || auth.error || historyLoaded) return
    const controller = new AbortController(); setError('')
    getChatHistory(controller.signal).then(history => {
      if (controller.signal.aborted) return
      setMessages(history); setHistoryLoaded(true)
      const last = [...history].reverse().find(message => message.role === 'assistant' && (message.search || message.products?.length))
      if (last) onResults(last)
    }).catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Could not load your chat.') })
    return () => controller.abort()
  }, [open, auth.user?.id, auth.loading, auth.error, historyLoaded, historyAttempt, onResults])
  function close() { setOpen(false); launcher.current?.focus() }
  async function send(event: React.FormEvent) {
    event.preventDefault()
    if (!draft.trim() || sending || auth.loading || !!auth.error || !historyLoaded) return
    const message = draft.trim(); setDraft(''); setSending(true); setError('')
    const controller = new AbortController(); sendingController.current = controller
    const timeout = window.setTimeout(() => controller.abort(), 70000)
    setMessages(old => [...old, { role: 'user', content: message }])
    try {
      const result = await sendChatMessage(message, controller.signal, pageContextFor(window.location.pathname))
      if (controller.signal.aborted) return
      setMessages(old => [...old, { role: 'assistant' as const, content: result.reply, products: result.products, search: result.search }].slice(auth.user ? -100 : -12))
      onResults(result)
    } catch (e) {
      setMessages(old => old.slice(0, -1)); setDraft(message)
      setError(e instanceof ChatError ? e.message : 'I couldn’t finish that reply. Please try sending your message again.')
      if (e instanceof ChatError && e.status === 401) void auth.refresh()
    } finally {
      window.clearTimeout(timeout); setSending(false); input.current?.focus()
    }
  }
  return <div className="chat-widget">{open && <section id="shopping-chat" className="chat-panel" role="dialog" aria-label="Handsome Dan shopping chat" onKeyDown={e => { if (e.key === 'Escape') close() }}>
    <header><Bulldog /><div><strong>Handsome Dan</strong><span>Your AI campus companion</span></div><button onClick={close} aria-label="Close chat">×</button></header>
    <div className="chat-messages" role="log" aria-live="polite">
      {!messages.length && <div className="chat-bubble assistant">Hi, I’m Handsome Dan! Looking for your next campus classic? Tell me your style, size, or budget and we’ll find your kind of blue.</div>}
      {!historyLoaded && !error && !auth.error && <p className="muted">Getting your chat ready…</p>}
      {messages.map((message, index) => <div className={`chat-entry ${message.role}`} key={index}><div className={`chat-bubble ${message.role}`}>{message.role === 'assistant' ? <><span className="chat-speaker">HANDSOME DAN</span><ChatText text={message.content} /></> : message.content}</div>{!!message.products?.length && <div className="chat-product-list">{message.products.map(product => <Link className="chat-product" key={product.product_id} to={`/products/${product.product_id}`} onClick={close}><img src={product.image_url} alt="" /><span>{product.name}<strong>{money(product.price)} ↗</strong></span></Link>)}</div>}</div>)}
      {sending && <p className="chat-thinking" role="status">Handsome Dan is checking the collection…</p>}
      <div ref={end} />
    </div>
    <div className="chat-starters" role="group" aria-label="Suggested questions"><p>A little inspiration</p><div>{suggestions.map(suggestion => <button key={suggestion.label} type="button" disabled={!!draft.trim() || sending || !historyLoaded || auth.loading || !!auth.error} onClick={() => { setDraft(suggestion.message); input.current?.focus() }}>{suggestion.label}</button>)}</div></div>
    {messages.some(message => message.search) && <Link className="chat-see-finds" to="/products#dan-finds" onClick={close}>See Handsome Dan’s finds on the page ↗</Link>}
    {error && <div className="chat-error" role="alert">{error}{!historyLoaded && <button onClick={() => setHistoryAttempt(a => a + 1)}>Try again</button>}</div>}
    {!auth.user && <div className="chat-login"><Link className="button" to="/login" onClick={close}>Log in to save your chats ↗</Link><p>New to the pack? <Link to="/create-account" onClick={close}>Create an account</Link></p></div>}
    {auth.error && <div className="chat-error" role="alert">{auth.error}<button onClick={() => void auth.refresh()}>Check account again</button></div>}
    <p className="chat-disclaimer">{auth.user ? 'Chats saved to your account. Showing your latest 100 messages.' : 'Guest chat is temporary. Log in to keep future conversations.'}{pageContext.page === 'product' && <><br />Handsome Dan can see which item you’re viewing.</>}<br />Catalogue-based answers. Stock can change.</p>
    <form onSubmit={send}><label className="sr-only" htmlFor="chat-input">Message Handsome Dan</label><input ref={input} id="chat-input" value={draft} maxLength={1000} disabled={auth.loading || !!auth.error || !historyLoaded || sending} onChange={e => setDraft(e.target.value)} placeholder={pageContext.page === 'product' ? 'Ask about this item…' : 'Ask about your next favorite…'} /><button disabled={!draft.trim() || sending || auth.loading || !!auth.error || !historyLoaded} aria-label="Send message">↑</button></form>
  </section>}
    <button ref={launcher} className="chat-launcher" aria-expanded={open} aria-controls="shopping-chat" aria-label={open ? 'Close Handsome Dan chat' : 'Chat with Handsome Dan'} onClick={() => open ? close() : setOpen(true)}><Bulldog /><span>{open ? 'Close chat' : 'Handsome Dan'}<small>{open ? 'See you around campus' : 'A little help finding your blue'}</small></span><b aria-hidden="true">{open ? '−' : '+'}</b></button>
  </div>
}

function SearchFinds({ finds, onHide }: { finds: ChatFinds; onHide: () => void }) {
  const search = finds.search
  const products = search?.products ?? finds.products ?? []
  return <section id="dan-finds" className="page-width chat-picks" aria-label="Handsome Dan’s finds">
    <div className="section-heading"><div className="finds-heading"><Bulldog /><div><p className="eyebrow">HANDSOME DAN’S FINDS</p><h2>Picked for you.</h2></div></div><button className="text-link" onClick={onHide}>Hide picks ×</button></div>
    {search && <><div className="finds-filters"><span>{search.query || 'All campus gear'}</span>{search.max_price !== null && <span>Up to {money(search.max_price)}</span>}{search.size && <span>Size {search.size}</span>}{search.in_stock_only && <span>In stock</span>}</div><p className="results-count" role="status">Showing {products.length} of {search.total_matches} {search.total_matches === 1 ? 'match' : 'matches'} · Open a card for the full story and size stock.</p></>}
    {products.length ? <div className="product-grid">{products.map(product => <ProductCard key={product.product_id} product={product} />)}</div> : <div className="finds-empty"><h3>No matches this time, bulldog.</h3><p>Try another style, a different size, or a wider budget with Handsome Dan.</p><Link className="text-link" to="/products">Explore the whole collection ↗</Link></div>}
  </section>
}

function App() {
  const auth = useAuth()
  const [finds, setFinds] = useState<ChatFinds | null>(null)
  const onResults = useCallback((result: ChatFinds) => {
    if (result.search || result.products?.length) setFinds(result)
  }, [])
  useEffect(() => setFinds(null), [auth.user?.id])
  const [products, setProducts] = useState<Product[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [attempt, setAttempt] = useState(0)
  const location = useLocation()
  useEffect(() => { window.scrollTo(0, 0) }, [location.pathname])
  useEffect(() => {
    const controller = new AbortController(); setLoading(true); setError('')
    getProducts(controller.signal).then(setProducts).catch(e => { if (!controller.signal.aborted) setError(e instanceof Error ? e.message : 'Unable to load products.') }).finally(() => { if (!controller.signal.aborted) setLoading(false) })
    return () => controller.abort()
  }, [attempt])
  const usesCatalogue = location.pathname === '/' || location.pathname.startsWith('/products')
  return <><a className="skip-link" href="#main">Skip to content</a><div className="announcement">A little campus spirit goes a long way. <Link to="/products">Find yours ↗</Link></div><header className="site-header"><div className="nav-wrap page-width"><Link className="brand" to="/" aria-label="Campus Customs home"><span className="brand-mark">Y</span><span>Campus Customs<small>NEW HAVEN, CONNECTICUT</small></span></Link><nav aria-label="Main navigation"><NavLink to="/" end>Home</NavLink><NavLink to="/products">Products</NavLink><NavLink to="/about">About us</NavLink></nav><div className="account-nav">{auth.user ? <NavLink className="join-link member-nav" to="/account">Hi, {auth.user.first_name || auth.user.name} ↗</NavLink> : <><NavLink to="/login">Log in</NavLink><NavLink className="join-link" to="/create-account">Join the pack ↗</NavLink></>}</div></div></header><main id="main">{usesCatalogue && <CatalogueStatus loading={loading} error={error} retry={() => setAttempt(a => a + 1)} />}{finds && !/^\/products\/[^/]+\/?$/.test(location.pathname) && <SearchFinds finds={finds} onHide={() => setFinds(null)} />}<Routes><Route path="/" element={<Home products={products} />} /><Route path="/products" element={loading || error ? null : <Products products={products} />} /><Route path="/products/:id" element={<ProductDetail products={products} loading={loading} error={error} />} /><Route path="/about" element={<About />} /><Route path="/login" element={<Account key="login" />} /><Route path="/create-account" element={<Account key="signup" create />} /><Route path="/account" element={<AccountHome />} /><Route path="*" element={<NotFound />} /></Routes></main><footer className="site-footer"><div className="page-width"><div><Link className="footer-brand" to="/">Campus Customs</Link><p>A little New Haven. Wherever you go.</p></div><div><Link to="/products">The collection</Link><Link to="/about">Our story</Link><Link to="/create-account">Create account</Link></div><p className="footer-note">HW4 student storefront · Prices shown in USD<br />Made with a little bulldog spirit.</p></div></footer><Chat key={auth.user?.id ?? 'guest'} onResults={onResults} /></>
}

createRoot(document.getElementById('root')!).render(<React.StrictMode><BrowserRouter><AuthProvider><App /></AuthProvider></BrowserRouter></React.StrictMode>)
