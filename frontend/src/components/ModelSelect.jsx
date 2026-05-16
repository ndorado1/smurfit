/**
 * Pantalla inicial de seleccion de proveedor LLM.
 * Antes de elegir usuario, el usuario decide si quiere usar:
 *  - El modelo comercial (OpenAI gpt-5.1)
 *  - El modelo open-source (Qwen3.5 via OpenRouter)
 */
const OPTIONS = [
  {
    id: 'commercial',
    title: 'Modelo Comercial',
    model: 'GPT-5.1 (OpenAI)',
    description: 'Maxima calidad. Requiere conexion a internet y API key. Los datos pasan por la nube.',
    color: 'bg-sw-600 hover:bg-sw-700',
    badge: 'bg-sw-100 text-sw-700',
    icon: '☁️',
  },
  {
    id: 'local',
    title: 'Modelo Open-Source',
    model: 'Qwen 3.5 9B (OpenRouter)',
    description: 'Modelo abierto ejecutado via OpenRouter. Mas economico que el comercial, calidad inferior pero competitiva.',
    color: 'bg-emerald-600 hover:bg-emerald-700',
    badge: 'bg-emerald-100 text-emerald-700',
    icon: '🖥️',
  },
]

export default function ModelSelect({ onSelect }) {
  return (
    <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-sw-50 via-white to-sw-100">
      <div className="max-w-4xl w-full px-6 py-10">
        <div className="text-center mb-10">
          <div className="w-20 h-20 mx-auto mb-4 bg-sw-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold shadow-lg">
            SW
          </div>
          <h1 className="text-3xl font-semibold text-sw-700 mb-2">
            Smurfit Westrock — Asistente Virtual
          </h1>
          <p className="text-slate-500">Primero, ¿con que modelo de LLM quieres trabajar?</p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          {OPTIONS.map((opt) => (
            <button
              key={opt.id}
              onClick={() => onSelect(opt.id)}
              className="group text-left bg-white border border-sw-100 hover:border-sw-400 hover:shadow-xl rounded-2xl p-6 transition-all"
            >
              <div className="flex items-center gap-3 mb-3">
                <div className={`w-12 h-12 rounded-xl ${opt.color} text-white text-2xl flex items-center justify-center transition-transform group-hover:scale-105`}>
                  {opt.icon}
                </div>
                <div>
                  <div className="font-semibold text-slate-800 text-lg">{opt.title}</div>
                  <span className={`text-xs px-2 py-0.5 rounded-full ${opt.badge}`}>
                    {opt.model}
                  </span>
                </div>
              </div>

              <p className="text-sm text-slate-600">{opt.description}</p>
            </button>
          ))}
        </div>

        <p className="text-xs text-slate-400 text-center mt-8">
          Podras cambiar de modelo en cualquier momento desde la barra lateral.
        </p>
      </div>
    </div>
  )
}
