import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const CANAL_BADGE = {
  web: 'bg-sw-100 text-sw-700',
  whatsapp: 'bg-emerald-100 text-emerald-700',
}

export default function Cotizaciones() {
  const [rows, setRows] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const refresh = async () => {
    try {
      setRows(await api.listCotizaciones())
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  return (
    <div className="flex-1 overflow-y-auto scroll-thin">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <div className="flex items-center justify-between mb-1">
          <h1 className="text-2xl font-semibold text-sw-700">📋 Cotizaciones</h1>
          <button onClick={refresh} className="text-sm text-sw-600 hover:text-sw-800">↻ Actualizar</button>
        </div>
        <p className="text-slate-500 mb-6">
          Leads comerciales registrados por el agente tras la aprobación humana (Human-in-the-Loop).
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">⚠ {error}</div>
        )}

        {loading ? (
          <div className="text-slate-400 text-sm">Cargando…</div>
        ) : rows.length === 0 ? (
          <div className="text-slate-400 text-sm">
            Aún no hay cotizaciones. Pide una en el chat (ej. <em>"Registra cotización: producto cajas, cantidad 5000, correo x@y.com"</em>) y aprueba la tarjeta.
          </div>
        ) : (
          <div className="overflow-x-auto border border-sw-100 rounded-xl">
            <table className="w-full text-sm">
              <thead className="bg-sw-50 text-slate-600">
                <tr>
                  <th className="text-left px-4 py-2 font-semibold">Producto</th>
                  <th className="text-left px-4 py-2 font-semibold">Cantidad</th>
                  <th className="text-left px-4 py-2 font-semibold">Correo</th>
                  <th className="text-left px-4 py-2 font-semibold">Cliente</th>
                  <th className="text-left px-4 py-2 font-semibold">Canal</th>
                  <th className="text-left px-4 py-2 font-semibold">Fecha</th>
                </tr>
              </thead>
              <tbody>
                {rows.map((c) => (
                  <tr key={c.id} className="border-t border-sw-100">
                    <td className="px-4 py-2 font-medium text-slate-700">{c.producto}</td>
                    <td className="px-4 py-2 text-slate-600">{c.cantidad}</td>
                    <td className="px-4 py-2 text-slate-600">{c.email_contacto}</td>
                    <td className="px-4 py-2 text-slate-600 capitalize">{c.nombre_cliente || '—'}</td>
                    <td className="px-4 py-2">
                      <span className={`text-xs px-2 py-0.5 rounded-full ${CANAL_BADGE[c.canal] || 'bg-slate-100 text-slate-600'}`}>
                        {c.canal}
                      </span>
                    </td>
                    <td className="px-4 py-2 text-slate-400 text-xs">
                      {new Date(c.created_at).toLocaleString('es-CO', { dateStyle: 'short', timeStyle: 'short' })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
