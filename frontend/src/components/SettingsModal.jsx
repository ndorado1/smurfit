import { useEffect, useState } from 'react'
import { DEFAULT_SAMPLING, getSettings, saveSettings, resetSettings } from '../lib/api'

function Slider({ label, value, min, max, step, onChange, help, format }) {
  const display = format ? format(value) : value
  return (
    <div className="mb-4">
      <div className="flex justify-between items-baseline mb-1">
        <label className="text-sm font-medium text-slate-700">{label}</label>
        <span className="text-xs font-mono text-sw-700 bg-sw-50 px-2 py-0.5 rounded">{display}</span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-sw-600"
      />
      {help && <p className="text-xs text-slate-400 mt-1">{help}</p>}
    </div>
  )
}

export default function SettingsModal({ provider, open, onClose }) {
  const [settings, setSettings] = useState(() => getSettings(provider))

  useEffect(() => {
    if (open) setSettings(getSettings(provider))
  }, [open, provider])

  if (!open) return null

  const update = (k, v) => setSettings((s) => ({ ...s, [k]: v }))

  const handleSave = () => {
    saveSettings(provider, settings)
    onClose()
  }

  const handleReset = () => {
    if (!confirm('¿Restaurar los valores por defecto?')) return
    resetSettings(provider)
    setSettings({ ...DEFAULT_SAMPLING[provider] })
  }

  const isLocal = provider === 'local'

  return (
    <div
      className="fixed inset-0 z-50 bg-slate-900/50 backdrop-blur-sm flex items-center justify-center p-4"
      onClick={onClose}
    >
      <div
        className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[90vh] overflow-y-auto"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-5 border-b border-sw-100 flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-sw-700">Parámetros de muestreo</h2>
            <p className="text-xs text-slate-500">
              {isLocal ? 'Modelo open-source (Qwen 3.5 9B via OpenRouter)' : 'Modelo comercial (GPT-5.1)'}
            </p>
          </div>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div className="p-5">
          <Slider
            label="Temperature"
            value={settings.temperature}
            min={0} max={2} step={0.1}
            onChange={(v) => update('temperature', v)}
            help="0 = determinista (siempre la misma respuesta). >1 = más creativo y aleatorio."
          />
          <Slider
            label="top_p (nucleus sampling)"
            value={settings.top_p}
            min={0} max={1} step={0.05}
            onChange={(v) => update('top_p', v)}
            help="Limita la probabilidad acumulada de los tokens candidatos."
          />

          {/* OpenRouter es OpenAI-compatible, asi que ambos modelos exponen
              los mismos parametros: frequency_penalty y presence_penalty. */}
          <Slider
            label="frequency_penalty"
            value={settings.frequency_penalty}
            min={-2} max={2} step={0.1}
            onChange={(v) => update('frequency_penalty', v)}
            help="Penaliza tokens según su frecuencia previa."
          />
          <Slider
            label="presence_penalty"
            value={settings.presence_penalty}
            min={-2} max={2} step={0.1}
            onChange={(v) => update('presence_penalty', v)}
            help="Penaliza tokens que ya aparecieron al menos una vez."
          />

          <Slider
            label="max_tokens"
            value={settings.max_tokens}
            min={128} max={8192} step={128}
            onChange={(v) => update('max_tokens', Math.round(v))}
            help="Tope de tokens a generar. Sube si las respuestas se cortan."
            format={(v) => Math.round(v)}
          />
        </div>

        <div className="p-5 border-t border-sw-100 flex justify-between gap-2">
          <button
            onClick={handleReset}
            className="text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded"
          >
            Restaurar
          </button>
          <div className="flex gap-2">
            <button
              onClick={onClose}
              className="text-sm text-slate-700 px-4 py-2 rounded-lg hover:bg-slate-100"
            >
              Cancelar
            </button>
            <button
              onClick={handleSave}
              className="text-sm bg-sw-600 hover:bg-sw-700 text-white px-4 py-2 rounded-lg font-medium"
            >
              Guardar
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
