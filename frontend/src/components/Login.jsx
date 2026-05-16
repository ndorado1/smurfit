import { useEffect, useState } from 'react'
import { api } from '../lib/api'

const AVATAR_COLORS = {
  antonio: 'bg-sw-600',
  bradley: 'bg-emerald-600',
  camilo:  'bg-amber-600',
  simon:   'bg-purple-600',
}

export default function Login({ onSelect }) {
  const [users, setUsers] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  useEffect(() => {
    api.listUsers()
      .then((r) => setUsers(r.users))
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  return (
    <div className="h-full w-full flex items-center justify-center bg-gradient-to-br from-sw-50 via-white to-sw-100">
      <div className="max-w-2xl w-full px-6">
        <div className="text-center mb-10">
          <div className="w-20 h-20 mx-auto mb-4 bg-sw-600 rounded-2xl flex items-center justify-center text-white text-3xl font-bold shadow-lg">
            SW
          </div>
          <h1 className="text-3xl font-semibold text-sw-700 mb-2">
            Smurfit Westrock — Asistente Virtual
          </h1>
          <p className="text-slate-500">¿Quién está consultando?</p>
        </div>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            ⚠ {error}
          </div>
        )}

        {loading ? (
          <div className="text-center text-slate-400">Cargando usuarios…</div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
            {users.map((u) => {
              const initial = u[0].toUpperCase()
              const color = AVATAR_COLORS[u] || 'bg-slate-500'
              return (
                <button
                  key={u}
                  onClick={() => onSelect(u)}
                  className="group flex flex-col items-center p-5 rounded-2xl bg-white border border-sw-100 hover:border-sw-400 hover:shadow-lg transition-all"
                >
                  <div className={`w-20 h-20 rounded-full ${color} text-white text-3xl font-bold flex items-center justify-center mb-3 group-hover:scale-105 transition-transform shadow`}>
                    {initial}
                  </div>
                  <div className="text-slate-700 font-medium capitalize">{u}</div>
                </button>
              )
            })}
          </div>
        )}

        <p className="text-xs text-slate-400 text-center mt-8">
          Cada usuario tiene su propio historial de conversaciones.
        </p>
      </div>
    </div>
  )
}
