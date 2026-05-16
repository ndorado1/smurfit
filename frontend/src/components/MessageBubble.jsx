import ReactMarkdown from 'react-markdown'

const TOOL_LABELS = {
  search_knowledge_base: { label: 'RAG', color: 'bg-emerald-100 text-emerald-700' },
  get_company_info:      { label: 'Datos estructurados', color: 'bg-amber-100 text-amber-700' },
}

export default function MessageBubble({ role, content, toolUsed, streaming = false }) {
  const isUser = role === 'user'
  const toolBadge = toolUsed && TOOL_LABELS[toolUsed]

  return (
    <div className={`flex ${isUser ? 'justify-end' : 'justify-start'} mb-4 gap-3`}>
      {!isUser && (
        <div className="w-8 h-8 rounded-full bg-sw-600 text-white flex items-center justify-center text-sm font-bold flex-shrink-0 mt-1">
          SW
        </div>
      )}
      <div className={`max-w-[75%] ${isUser ? 'order-1' : ''}`}>
        {toolBadge && !streaming && (
          <div className={`inline-block text-xs px-2 py-0.5 rounded-full mb-1 ${toolBadge.color}`}>
            🛠 {toolBadge.label}
          </div>
        )}
        <div
          className={`px-4 py-3 rounded-2xl ${
            isUser
              ? 'bg-sw-600 text-white rounded-tr-sm'
              : 'bg-sw-50 text-slate-800 rounded-tl-sm border border-sw-100'
          }`}
        >
          {isUser ? (
            <p className="whitespace-pre-wrap">{content}</p>
          ) : (
            <div className="prose-chat text-sm leading-relaxed">
              <ReactMarkdown>{content}</ReactMarkdown>
              {streaming && <span className="inline-block w-2 h-4 bg-sw-500 ml-0.5 animate-pulse align-middle" />}
            </div>
          )}
        </div>
      </div>
      {isUser && (
        <div className="w-8 h-8 rounded-full bg-slate-300 text-slate-700 flex items-center justify-center text-sm font-bold flex-shrink-0 mt-1">
          TÚ
        </div>
      )}
    </div>
  )
}
