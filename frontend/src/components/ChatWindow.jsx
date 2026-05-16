import { useEffect, useRef } from 'react'
import MessageBubble from './MessageBubble'
import MessageSkeleton from './MessageSkeleton'
import ThinkingIndicator from './ThinkingIndicator'

const SAMPLE_QUESTIONS = [
  '¿Cuál es el horario de atención al cliente?',
  '¿Cuántas plantas tiene Smurfit Kappa en Colombia?',
  '¿Qué es la cartulina Óptima?',
  '¿Cuál es el NIT de la empresa?',
  'Háblame de sus compromisos de sostenibilidad',
  '¿En qué dirección está la planta de Bogotá?',
]

export default function ChatWindow({ messages, loading, messagesLoading, streamingState, onPickSample }) {
  const endRef = useRef(null)

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading, streamingState])

  // streamingState: { phase: 'thinking'|'streaming'|null, activeTool, completedTools, buffer }
  const phase = streamingState?.phase

  // Estado de carga al cambiar de chat: skeleton placeholder
  if (messagesLoading) {
    return (
      <div className="flex-1 overflow-y-auto scroll-thin px-4 py-6">
        <div className="max-w-3xl mx-auto">
          <MessageSkeleton />
        </div>
      </div>
    )
  }

  if (messages.length === 0) {
    return (
      <div className="flex-1 overflow-y-auto scroll-thin flex items-center justify-center px-6">
        <div className="max-w-2xl text-center">
          <div className="w-16 h-16 mx-auto mb-4 bg-sw-600 rounded-2xl flex items-center justify-center text-white text-2xl font-bold">
            SW
          </div>
          <h1 className="text-2xl font-semibold text-sw-700 mb-2">
            Asistente Virtual Smurfit Westrock
          </h1>
          <p className="text-slate-500 mb-8">
            Hago dos cosas: respondo con documentos oficiales (RAG) o consulto la base de datos estructurada de la empresa. Pruebame:
          </p>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-left">
            {SAMPLE_QUESTIONS.map((q) => (
              <button
                key={q}
                onClick={() => onPickSample(q)}
                className="px-4 py-3 rounded-xl border border-sw-100 hover:border-sw-300 hover:bg-sw-50 transition-colors text-sm text-slate-700"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="flex-1 overflow-y-auto scroll-thin px-4 py-6">
      <div className="max-w-3xl mx-auto">
        {messages.map((m) => (
          <MessageBubble key={m.id} role={m.role} content={m.content} toolUsed={m.tool_used} />
        ))}

        {phase === 'thinking' && (
          <ThinkingIndicator
            activeTool={streamingState.activeTool}
            completedTools={streamingState.completedTools}
          />
        )}

        {phase === 'streaming' && (
          <MessageBubble
            role="assistant"
            content={streamingState.buffer}
            toolUsed={streamingState.completedTools[0]}
            streaming
          />
        )}

        <div ref={endRef} />
      </div>
    </div>
  )
}
