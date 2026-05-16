// Cliente del backend FastAPI. El proxy de Vite redirige /api -> http://localhost:8000

const BASE = '/api'
const USER_KEY = 'sw_user'
const PROVIDER_KEY = 'sw_provider'
const SETTINGS_PREFIX = 'sw_settings_'  // sw_settings_commercial, sw_settings_local

export const DEFAULT_SAMPLING = {
  commercial: {
    temperature: 0.2,
    top_p: 1.0,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    max_tokens: 2048,
  },
  local: {
    temperature: 0.2,
    top_p: 0.9,
    frequency_penalty: 0.0,
    presence_penalty: 0.0,
    max_tokens: 2048,
  },
}

export function getSettings(provider) {
  try {
    const raw = localStorage.getItem(SETTINGS_PREFIX + provider)
    if (!raw) return { ...DEFAULT_SAMPLING[provider] }
    return { ...DEFAULT_SAMPLING[provider], ...JSON.parse(raw) }
  } catch {
    return { ...DEFAULT_SAMPLING[provider] }
  }
}

export function saveSettings(provider, settings) {
  localStorage.setItem(SETTINGS_PREFIX + provider, JSON.stringify(settings))
}

export function resetSettings(provider) {
  localStorage.removeItem(SETTINGS_PREFIX + provider)
}

export function getCurrentUser() {
  return localStorage.getItem(USER_KEY)
}

export function setCurrentUser(user) {
  localStorage.setItem(USER_KEY, user)
}

export function clearCurrentUser() {
  localStorage.removeItem(USER_KEY)
}

export function getCurrentProvider() {
  return localStorage.getItem(PROVIDER_KEY)
}

export function setCurrentProvider(provider) {
  localStorage.setItem(PROVIDER_KEY, provider)
}

export function clearCurrentProvider() {
  localStorage.removeItem(PROVIDER_KEY)
}

// Endpoints publicos que no requieren X-User-Id
const PUBLIC_PATHS = ['/users', '/health']

async function req(path, opts = {}) {
  const user = getCurrentUser()
  const provider = getCurrentProvider()
  const isPublic = PUBLIC_PATHS.some((p) => path === p || path.startsWith(p + '?'))

  if (!user && !isPublic) {
    // Sin usuario no se hacen llamadas autenticadas (evita 401 falsos).
    throw new Error('Sin sesion. Selecciona un usuario primero.')
  }

  const headers = { 'Content-Type': 'application/json', ...(opts.headers || {}) }
  if (user) headers['X-User-Id'] = user
  if (provider) headers['X-Model-Provider'] = provider

  const res = await fetch(BASE + path, { ...opts, headers })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }
  return res.json()
}

function _currentSampling() {
  const provider = getCurrentProvider()
  return provider ? getSettings(provider) : null
}

export const api = {
  listUsers:   ()             => req('/users'),
  listChats:   ()             => req('/chats'),
  createChat:  (title)        => req('/chats', { method: 'POST', body: JSON.stringify({ title }) }),
  deleteChat:  (id)           => req(`/chats/${id}`, { method: 'DELETE' }),
  renameChat:  (id, title)    => req(`/chats/${id}`, { method: 'PATCH', body: JSON.stringify({ title }) }),
  getMessages: (id)           => req(`/chats/${id}/messages`),
  sendMessage: (id, content)  => req(`/chats/${id}/messages`, {
    method: 'POST',
    body: JSON.stringify({ content, sampling: _currentSampling() }),
  }),
}

/**
 * Envia un mensaje y procesa la respuesta como Server-Sent Events.
 * Llama a `onEvent(eventObj)` por cada evento recibido:
 *
 *   { type: 'tool_start', tool: '...' }
 *   { type: 'tool_end',   tool: '...' }
 *   { type: 'token',      content: '...' }
 *   { type: 'done',       answer: '...', tools_used: [...] }
 *   { type: 'error',      message: '...' }
 */
export async function streamMessage(chatId, content, onEvent) {
  const user = getCurrentUser()
  const provider = getCurrentProvider() || 'commercial'
  if (!user) throw new Error('Sin sesion. Selecciona un usuario primero.')

  const res = await fetch(`${BASE}/chats/${chatId}/messages/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-User-Id': user,
      'X-Model-Provider': provider,
      'Accept': 'text/event-stream',
    },
    body: JSON.stringify({ content, sampling: _currentSampling() }),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`${res.status}: ${text}`)
  }

  const reader = res.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  let streamError = null

  while (true) {
    const { done, value } = await reader.read()
    if (done) break
    buffer += decoder.decode(value, { stream: true })

    // SSE separa eventos por linea en blanco. Una linea de datos: "data: {...}\n"
    let idx
    while ((idx = buffer.indexOf('\n\n')) !== -1) {
      const block = buffer.slice(0, idx)
      buffer = buffer.slice(idx + 2)
      for (const line of block.split('\n')) {
        if (!line.startsWith('data:')) continue
        const raw = line.slice(5).trim()
        if (!raw) continue
        let parsed
        try {
          parsed = JSON.parse(raw)
        } catch (e) {
          console.warn('SSE parse error', e, raw)
          continue
        }
        // Capturar errores del backend para lanzarlos al final del stream
        if (parsed.type === 'error') {
          streamError = parsed.message
        }
        try {
          onEvent(parsed)
        } catch (e) {
          // No silenciar errores de la callback
          streamError = e.message
        }
      }
    }
  }

  if (streamError) {
    throw new Error(streamError)
  }
}
