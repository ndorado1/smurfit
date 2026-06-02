import { useEffect, useState, useCallback, useRef } from 'react'
import Sidebar from './components/Sidebar'
import ChatWindow from './components/ChatWindow'
import ChatInput from './components/ChatInput'
import Login from './components/Login'
import ModelSelect from './components/ModelSelect'
import SettingsModal from './components/SettingsModal'
import Training from './components/Training'
import Cotizaciones from './components/Cotizaciones'
import {
  api, streamMessage, resumeMessage,
  getCurrentUser, setCurrentUser, clearCurrentUser,
  getCurrentProvider, setCurrentProvider, clearCurrentProvider,
} from './lib/api'

export default function App() {
  const [currentUser, setUser] = useState(() => getCurrentUser())
  const [currentProvider, setProvider] = useState(() => getCurrentProvider())
  const [settingsOpen, setSettingsOpen] = useState(false)
  const [view, setView] = useState('chat')  // 'chat' | 'training'
  const [chats, setChats] = useState([])
  const [activeId, setActiveId] = useState(null)
  const [messages, setMessages] = useState([])
  const [messagesLoading, setMessagesLoading] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  // streamingState describe la respuesta en curso del agente:
  //   phase: null | 'thinking' | 'streaming'
  //   activeTool: tool corriendo ahora (o null)
  //   completedTools: tools que ya retornaron
  //   buffer: texto acumulado de tokens del agente
  // Aprobacion HITL pendiente: { tool, args, description } o null
  const [pendingApproval, setPendingApproval] = useState(null)
  const [streamingState, setStreamingState] = useState({
    phase: null, activeTool: null, completedTools: [], buffer: '',
  })

  // Cuando handleSend crea un nuevo chat o ya inserto un mensaje optimista,
  // activa esta flag para que el useEffect que carga mensajes al cambiar
  // activeId no pise el estado local.
  const skipNextFetch = useRef(false)

  const refreshChats = useCallback(async () => {
    try {
      const list = await api.listChats()
      setChats(list)
      return list
    } catch (e) {
      setError(e.message)
      return []
    }
  }, [])

  // Carga inicial (solo si hay usuario)
  useEffect(() => {
    if (currentUser) refreshChats()
  }, [refreshChats, currentUser])

  const handleSelectProvider = (provider) => {
    setCurrentProvider(provider)
    setProvider(provider)
    setError(null)
  }

  const handleChangeProvider = () => {
    if (!confirm('¿Cambiar de modelo? La conversación actual seguirá pero las próximas respuestas usarán el modelo nuevo.')) return
    clearCurrentProvider()
    setProvider(null)
  }

  const handleLogin = (user) => {
    setCurrentUser(user)
    setUser(user)
    setActiveId(null)
    setMessages([])
    setError(null)  // limpia errores residuales (ej. 401 antes de logear)
  }

  const handleLogout = () => {
    if (!confirm('¿Cambiar de usuario? Tu sesión actual se cerrará.')) return
    clearCurrentUser()
    setUser(null)
    setActiveId(null)
    setMessages([])
    setChats([])
    setError(null)
  }

  // Cargar mensajes al cambiar de chat (solo cuando el usuario selecciona uno)
  useEffect(() => {
    setPendingApproval(null)  // descarta aprobaciones pendientes de otro chat
    if (!activeId) { setMessages([]); setMessagesLoading(false); return }
    if (skipNextFetch.current) {
      skipNextFetch.current = false
      return
    }
    setMessagesLoading(true)
    setMessages([])  // limpia inmediatamente para que solo se vea el skeleton
    api.getMessages(activeId)
      .then(setMessages)
      .catch((e) => setError(e.message))
      .finally(() => setMessagesLoading(false))
  }, [activeId])

  const handleNewChat = async () => {
    try {
      const chat = await api.createChat()
      await refreshChats()
      skipNextFetch.current = true  // chat recien creado, sabemos que esta vacio
      setActiveId(chat.id)
      setMessages([])
    } catch (e) { setError(e.message) }
  }

  const handleDeleteChat = async (id) => {
    if (!confirm('¿Eliminar esta conversación?')) return
    try {
      await api.deleteChat(id)
      if (id === activeId) { setActiveId(null); setMessages([]) }
      await refreshChats()
    } catch (e) { setError(e.message) }
  }

  const handleSend = async (text) => {
    setError(null)
    let chatId = activeId
    let isNewChat = false
    if (!chatId) {
      const chat = await api.createChat()
      chatId = chat.id
      isNewChat = true
    }

    // Optimistic UI: inserta el mensaje del usuario YA
    const tmpId = 'tmp-' + Date.now()
    setMessages((prev) => [
      ...prev,
      { id: tmpId, role: 'user', content: text, tool_used: null },
    ])
    setLoading(true)

    // Si era un chat nuevo, activar la flag ANTES de cambiar activeId
    // para que el useEffect no haga fetch (que devolveria [] y borraria el mensaje)
    if (isNewChat) {
      skipNextFetch.current = true
      setActiveId(chatId)
    }

    // Inicializa el estado de streaming
    setStreamingState({ phase: 'thinking', activeTool: null, completedTools: [], buffer: '' })

    await consumeStream(
      chatId,
      (onEvent) => streamMessage(chatId, text, onEvent),
      () => setMessages((prev) => prev.filter((m) => m.id !== tmpId)),
    )
  }

  // Consume un stream del agente (enviar o reanudar) con manejo comun de
  // eventos, incluido el interrupt de Human-in-the-Loop.
  const consumeStream = async (chatId, runner, onError) => {
    let interrupted = false
    try {
      await runner((ev) => {
        if (ev.type === 'tool_start') {
          setStreamingState((s) => ({ ...s, phase: 'thinking', activeTool: ev.tool }))
        } else if (ev.type === 'tool_end') {
          setStreamingState((s) => ({ ...s, activeTool: null, completedTools: [...s.completedTools, ev.tool] }))
        } else if (ev.type === 'token') {
          setStreamingState((s) => ({ ...s, phase: 'streaming', activeTool: null, buffer: s.buffer + ev.content }))
        } else if (ev.type === 'interrupt') {
          interrupted = true
          setPendingApproval({ tool: ev.tool, args: ev.args || {}, description: ev.description || '' })
        } else if (ev.type === 'error') {
          throw new Error(ev.message)
        }
      })

      if (!interrupted) {
        const [fresh] = await Promise.all([api.getMessages(chatId), refreshChats()])
        setMessages(fresh)
      }
    } catch (e) {
      setError(e.message)
      onError?.()
    } finally {
      setLoading(false)
      setStreamingState({ phase: null, activeTool: null, completedTools: [], buffer: '' })
    }
  }

  // Respuesta del humano a la aprobacion HITL (approve / reject)
  const handleApproval = async (decision) => {
    if (!activeId) return
    setPendingApproval(null)
    setLoading(true)
    setStreamingState({ phase: 'thinking', activeTool: null, completedTools: [], buffer: '' })
    await consumeStream(
      activeId,
      (onEvent) => resumeMessage(activeId, decision, null, onEvent),
    )
  }

  const handleSelectChat = (id) => {
    if (id === activeId) return
    setActiveId(id)  // el useEffect se encarga de cargar los mensajes
  }

  // Flujo de pantallas: 1) ModelSelect, 2) Login, 3) Chat
  if (!currentProvider) {
    return <ModelSelect onSelect={handleSelectProvider} />
  }
  if (!currentUser) {
    return <Login onSelect={handleLogin} />
  }

  return (
    <div className="h-full flex">
      <Sidebar
        chats={chats}
        activeId={activeId}
        onSelect={handleSelectChat}
        onNew={handleNewChat}
        onDelete={handleDeleteChat}
        currentUser={currentUser}
        onLogout={handleLogout}
        currentProvider={currentProvider}
        onChangeProvider={handleChangeProvider}
        onOpenSettings={() => setSettingsOpen(true)}
        view={view}
        onChangeView={setView}
      />

      <SettingsModal
        provider={currentProvider}
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />

      <main className="flex-1 flex flex-col bg-white">
        {view === 'training' ? (
          <Training />
        ) : view === 'cotizaciones' ? (
          <Cotizaciones />
        ) : (
          <>
            <header className="border-b border-sw-100 px-6 py-3 flex items-center justify-between">
              <div>
                <h2 className="font-semibold text-sw-700">
                  {activeId ? (chats.find((c) => c.id === activeId)?.title || 'Conversación') : 'Inicio'}
                </h2>
                <p className="text-xs text-slate-400">
                  {activeId ? 'Conversación activa' : 'Selecciona o crea una conversación para empezar'}
                </p>
              </div>
              <div className="text-xs text-slate-400">
                Agente LangChain · RAG + Function Calling
              </div>
            </header>

            {error && (
              <div className="bg-red-50 border-b border-red-200 px-4 py-2 text-sm text-red-700">
                ⚠ {error}
              </div>
            )}

            <ChatWindow
              messages={messages}
              loading={loading}
              messagesLoading={messagesLoading}
              streamingState={streamingState}
              pendingApproval={pendingApproval}
              onApprovalDecision={handleApproval}
              currentUser={currentUser}
              onPickSample={handleSend}
            />
            <ChatInput onSend={handleSend} disabled={loading || !!pendingApproval} />
          </>
        )}
      </main>
    </div>
  )
}
