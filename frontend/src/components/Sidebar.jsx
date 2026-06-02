import { useState } from 'react'

const AVATAR_COLORS = {
  antonio: 'bg-sw-500',
  bradley: 'bg-emerald-500',
  camilo:  'bg-amber-500',
  simon:   'bg-purple-500',
}

const PROVIDER_INFO = {
  commercial: { label: 'GPT-5.1', icon: '☁️', color: 'bg-sw-500' },
  local:      { label: 'Qwen3.5:9B', icon: '🖥️', color: 'bg-emerald-500' },
}

export default function Sidebar({
  chats, activeId, onSelect, onNew, onDelete,
  currentUser, onLogout, currentProvider, onChangeProvider, onOpenSettings,
  view = 'chat', onChangeView,
}) {
  const [hoverId, setHoverId] = useState(null)
  const avatarColor = AVATAR_COLORS[currentUser] || 'bg-slate-500'
  const providerInfo = PROVIDER_INFO[currentProvider] || PROVIDER_INFO.commercial

  return (
    <aside className="w-72 h-full bg-sw-700 text-white flex flex-col border-r border-sw-800">
      <div className="p-4 border-b border-sw-800">
        <div className="flex items-center gap-2 mb-3">
          <div className="w-8 h-8 bg-white rounded flex items-center justify-center text-sw-700 font-bold text-sm">
            SW
          </div>
          <div>
            <div className="font-semibold text-sm leading-tight">Smurfit Westrock</div>
            <div className="text-xs text-sw-200">Asistente Virtual</div>
          </div>
        </div>

        {/* Navegacion Chat / Entrenamiento */}
        <div className="flex gap-1 bg-sw-800/60 rounded-lg p-1 mb-3">
          <button
            onClick={() => onChangeView?.('chat')}
            className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
              view === 'chat' ? 'bg-white text-sw-700' : 'text-sw-100 hover:bg-sw-800'
            }`}
          >
            💬 Chat
          </button>
          <button
            onClick={() => onChangeView?.('training')}
            className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
              view === 'training' ? 'bg-white text-sw-700' : 'text-sw-100 hover:bg-sw-800'
            }`}
          >
            🎓 Entrenar
          </button>
          <button
            onClick={() => onChangeView?.('cotizaciones')}
            className={`flex-1 px-2 py-1.5 rounded-md text-xs font-medium transition-colors ${
              view === 'cotizaciones' ? 'bg-white text-sw-700' : 'text-sw-100 hover:bg-sw-800'
            }`}
          >
            📋 Leads
          </button>
        </div>

        <button
          onClick={onNew}
          disabled={view !== 'chat'}
          className="w-full bg-white text-sw-700 hover:bg-sw-50 transition-colors px-3 py-2 rounded-lg text-sm font-medium flex items-center justify-center gap-2 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          Nueva conversación
        </button>
      </div>

      <div className="flex-1 overflow-y-auto scroll-thin px-2 py-2">
        <div className="text-xs uppercase tracking-wider text-sw-200 px-2 mb-1">
          Historial
        </div>
        {chats.length === 0 && (
          <div className="text-sm text-sw-200 px-2 py-3">
            Aún no tienes conversaciones.
          </div>
        )}
        {chats.map((c) => (
          <div
            key={c.id}
            onMouseEnter={() => setHoverId(c.id)}
            onMouseLeave={() => setHoverId(null)}
            className={`group flex items-center gap-2 px-2 py-2 rounded-lg cursor-pointer text-sm mb-0.5 transition-colors ${
              activeId === c.id
                ? 'bg-sw-800 text-white'
                : 'hover:bg-sw-800/60 text-sw-100'
            }`}
            onClick={() => onSelect(c.id)}
          >
            <svg className="w-4 h-4 flex-shrink-0 opacity-70" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
            </svg>
            <span className="flex-1 truncate">{c.title}</span>
            {hoverId === c.id && (
              <button
                onClick={(e) => { e.stopPropagation(); onDelete(c.id) }}
                className="opacity-70 hover:opacity-100 hover:text-red-300"
                title="Eliminar"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3" />
                </svg>
              </button>
            )}
          </div>
        ))}
      </div>

      <div className="p-3 border-t border-sw-800 space-y-2">
        {/* Selector de modelo + boton de ajustes */}
        <div className="flex items-center gap-1">
          <button
            onClick={onChangeProvider}
            className="flex-1 flex items-center gap-2 px-2 py-2 rounded-lg hover:bg-sw-800 transition-colors group"
            title="Cambiar modelo"
          >
            <div className={`w-7 h-7 rounded ${providerInfo.color} text-white flex items-center justify-center text-base flex-shrink-0`}>
              {providerInfo.icon}
            </div>
            <div className="flex-1 min-w-0 text-left">
              <div className="text-xs text-sw-200">Modelo</div>
              <div className="text-sm font-medium truncate">{providerInfo.label}</div>
            </div>
          </button>
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg text-sw-200 hover:text-white hover:bg-sw-800 transition-colors"
            title="Parámetros del modelo"
          >
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            </svg>
          </button>
        </div>

        {/* Usuario actual */}
        <div className="flex items-center gap-2">
          <div className={`w-9 h-9 rounded-full ${avatarColor} text-white font-bold flex items-center justify-center text-sm flex-shrink-0`}>
            {currentUser?.[0]?.toUpperCase() || '?'}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium capitalize truncate">{currentUser}</div>
            <div className="text-xs text-sw-200">Sesión activa</div>
          </div>
          <button
            onClick={onLogout}
            className="text-sw-200 hover:text-white p-1 rounded hover:bg-sw-800 transition-colors"
            title="Cambiar usuario"
          >
            <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1" />
            </svg>
          </button>
        </div>
      </div>
    </aside>
  )
}
