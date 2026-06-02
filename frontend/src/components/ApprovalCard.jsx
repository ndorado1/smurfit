const ARG_LABELS = {
  producto: 'Producto',
  cantidad: 'Cantidad',
  email_contacto: 'Correo de contacto',
  nombre_cliente: 'Cliente',
}

/**
 * Tarjeta de aprobacion Human-in-the-Loop. Se muestra cuando el agente quiere
 * ejecutar una accion critica (registrar una cotizacion) y requiere que un
 * humano apruebe o rechace antes de continuar.
 */
export default function ApprovalCard({ approval, onDecision, disabled, currentUser }) {
  const { tool, args } = approval
  // Si el LLM no capturo el cliente, mostramos el perfil de la sesion.
  const displayArgs = {
    ...args,
    nombre_cliente: args.nombre_cliente || currentUser || '',
  }
  return (
    <div className="flex justify-start mb-4 gap-3">
      <div className="w-8 h-8 rounded-full bg-amber-500 text-white flex items-center justify-center text-sm font-bold flex-shrink-0 mt-1">
        ⚠
      </div>
      <div className="max-w-[80%] rounded-2xl rounded-tl-sm border-2 border-amber-300 bg-amber-50 p-4">
        <div className="font-semibold text-amber-800 mb-1">Acción pendiente de aprobación</div>
        <p className="text-sm text-amber-700 mb-3">
          El asistente quiere ejecutar <code className="bg-amber-100 px-1 rounded">{tool || 'una acción crítica'}</code>.
          Revisa los datos y aprueba o rechaza.
        </p>

        <div className="bg-white rounded-lg border border-amber-200 p-3 mb-3 text-sm">
          {Object.entries(displayArgs).map(([k, v]) => (
            <div key={k} className="flex gap-2 py-0.5">
              <span className="text-slate-500 min-w-[120px]">{ARG_LABELS[k] || k}:</span>
              <span className="font-medium text-slate-800">{String(v) || '—'}</span>
            </div>
          ))}
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => onDecision('approve')}
            disabled={disabled}
            className="bg-emerald-600 hover:bg-emerald-700 disabled:opacity-50 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            ✓ Aprobar
          </button>
          <button
            onClick={() => onDecision('reject')}
            disabled={disabled}
            className="bg-white hover:bg-red-50 disabled:opacity-50 text-red-600 border border-red-200 text-sm font-medium px-4 py-2 rounded-lg transition-colors"
          >
            ✕ Rechazar
          </button>
        </div>
      </div>
    </div>
  )
}
