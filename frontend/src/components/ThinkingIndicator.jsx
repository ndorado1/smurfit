const TOOL_INFO = {
  search_knowledge_base: {
    label: 'Buscando en la base de conocimiento',
    icon: '📚',
    color: 'text-emerald-700 bg-emerald-50 border-emerald-200',
  },
  get_company_info: {
    label: 'Consultando datos estructurados',
    icon: '🗂️',
    color: 'text-amber-700 bg-amber-50 border-amber-200',
  },
}

export default function ThinkingIndicator({ activeTool, completedTools }) {
  const tool = activeTool ? TOOL_INFO[activeTool] : null

  return (
    <div className="flex justify-start mb-4">
      <div className="w-8 h-8 rounded-full bg-sw-600 text-white flex items-center justify-center text-sm font-bold mr-2 flex-shrink-0">
        SW
      </div>
      <div className="bg-sw-50 border border-sw-100 px-4 py-3 rounded-2xl rounded-tl-sm max-w-[75%]">
        <div className="text-xs text-slate-500 mb-1 flex items-center gap-1">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="ml-1">Pensando…</span>
        </div>

        {completedTools.length > 0 && (
          <div className="space-y-1 mt-2">
            {completedTools.map((t, i) => {
              const info = TOOL_INFO[t]
              if (!info) return null
              return (
                <div key={i} className={`text-xs px-2 py-1 rounded border ${info.color} inline-flex items-center gap-1 mr-1`}>
                  <span>✓ {info.icon}</span>
                  <span className="font-medium">{info.label}</span>
                </div>
              )
            })}
          </div>
        )}

        {tool && (
          <div className={`text-xs px-2 py-1 rounded border ${tool.color} inline-flex items-center gap-1 mt-1`}>
            <span className="animate-pulse">{tool.icon}</span>
            <span className="font-medium">{tool.label}…</span>
          </div>
        )}
      </div>
    </div>
  )
}
