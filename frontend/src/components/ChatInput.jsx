import { useState, useRef, useEffect } from 'react'

export default function ChatInput({ onSend, disabled }) {
  const [text, setText] = useState('')
  const ref = useRef(null)

  useEffect(() => {
    const el = ref.current
    if (!el) return
    el.style.height = 'auto'
    el.style.height = Math.min(el.scrollHeight, 200) + 'px'
  }, [text])

  const submit = () => {
    if (!text.trim() || disabled) return
    onSend(text.trim())
    setText('')
  }

  const handleKey = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      submit()
    }
  }

  return (
    <div className="border-t border-sw-100 bg-white px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-2">
        <textarea
          ref={ref}
          rows={1}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onKeyDown={handleKey}
          placeholder="Pregunta sobre Smurfit Westrock Colombia… (Enter para enviar)"
          disabled={disabled}
          className="flex-1 resize-none px-4 py-3 rounded-2xl border border-sw-100 focus:outline-none focus:ring-2 focus:ring-sw-400 focus:border-transparent text-sm disabled:bg-slate-50"
        />
        <button
          onClick={submit}
          disabled={disabled || !text.trim()}
          className="bg-sw-600 hover:bg-sw-700 disabled:bg-slate-300 text-white rounded-full w-11 h-11 flex items-center justify-center transition-colors flex-shrink-0"
          title="Enviar (Enter)"
        >
          <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M12 19l9-7-9-7m0 14l-9-7 9-7" transform="rotate(90 12 12)" />
          </svg>
        </button>
      </div>
      <div className="max-w-3xl mx-auto text-xs text-slate-400 mt-2 text-center">
        El asistente usa RAG sobre documentos oficiales y una base de datos estructurada de la empresa.
      </div>
    </div>
  )
}
