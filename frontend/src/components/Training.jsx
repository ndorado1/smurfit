import { useEffect, useRef, useState } from 'react'
import { api, kbUpload } from '../lib/api'

function StatCard({ label, value, sub, accent }) {
  return (
    <div className="bg-white border border-sw-100 rounded-xl p-4">
      <div className="text-xs text-slate-500 uppercase tracking-wide">{label}</div>
      <div className={`text-2xl font-bold mt-1 ${accent || 'text-sw-700'}`}>{value}</div>
      {sub && <div className="text-xs text-slate-400 mt-0.5">{sub}</div>}
    </div>
  )
}

export default function Training() {
  const [status, setStatus] = useState(null)
  const [docs, setDocs] = useState([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState(null)
  const [flash, setFlash] = useState(null)
  const [dragOver, setDragOver] = useState(false)
  const fileRef = useRef(null)

  const refresh = async () => {
    try {
      const [s, d] = await Promise.all([api.kbStatus(), api.kbDocuments()])
      setStatus(s)
      setDocs(d)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const handleFile = async (file) => {
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError('Solo se aceptan archivos PDF.')
      return
    }
    setError(null); setFlash(null); setUploading(true)
    try {
      const r = await kbUpload(file)
      setFlash(`✓ "${r.filename}" procesado: ${r.chunks} chunks agregados a la base de conocimiento.`)
      await refresh()
    } catch (e) {
      setError(e.message)
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleDelete = async (doc) => {
    if (!confirm(`¿Eliminar "${doc.filename}" y sus ${doc.chunk_count} chunks de la base de conocimiento?`)) return
    try {
      await api.kbDelete(doc.doc_id)
      await refresh()
    } catch (e) {
      setError(e.message)
    }
  }

  return (
    <div className="flex-1 overflow-y-auto scroll-thin">
      <div className="max-w-4xl mx-auto px-6 py-6">
        <h1 className="text-2xl font-semibold text-sw-700 mb-1">🎓 Entrenamiento</h1>
        <p className="text-slate-500 mb-6">
          Enriquece la base de conocimiento del asistente subiendo documentos PDF.
          Se procesan, dividen en fragmentos y se indexan semánticamente al instante.
        </p>

        {error && (
          <div className="mb-4 p-3 rounded-lg bg-red-50 border border-red-200 text-red-700 text-sm">
            ⚠ {error}
          </div>
        )}
        {flash && (
          <div className="mb-4 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-700 text-sm">
            {flash}
          </div>
        )}

        {/* Dashboard de estado */}
        <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-2">
          Estado de la base de conocimiento
        </h2>
        {loading ? (
          <div className="text-slate-400 text-sm mb-6">Cargando…</div>
        ) : status && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-8">
            <StatCard label="Chunks totales" value={status.total_chunks} accent="text-sw-700" />
            <StatCard label="Del sitio web" value={status.chunks_web_scraping} sub="scraping" />
            <StatCard label="De PDFs" value={status.chunks_pdf} sub={`${status.documentos_pdf} documentos`} accent="text-emerald-600" />
            <StatCard label="Dimensiones" value={status.dimensiones} sub={status.modelo_embeddings} />
          </div>
        )}

        {/* Zona de carga */}
        <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-2">
          Subir documento
        </h2>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
          onDragLeave={() => setDragOver(false)}
          onDrop={(e) => {
            e.preventDefault(); setDragOver(false)
            if (!uploading) handleFile(e.dataTransfer.files?.[0])
          }}
          onClick={() => !uploading && fileRef.current?.click()}
          className={`border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer transition-colors mb-8 ${
            dragOver ? 'border-sw-400 bg-sw-50' : 'border-sw-200 hover:border-sw-300 hover:bg-sw-50/50'
          } ${uploading ? 'opacity-60 pointer-events-none' : ''}`}
        >
          <input ref={fileRef} type="file" accept=".pdf" className="hidden"
                 onChange={(e) => handleFile(e.target.files?.[0])} />
          {uploading ? (
            <div className="text-sw-600">
              <div className="flex justify-center gap-1 mb-2">
                <span className="typing-dot" /><span className="typing-dot" /><span className="typing-dot" />
              </div>
              Procesando PDF: extrayendo texto → chunking → embeddings…
            </div>
          ) : (
            <div className="text-slate-500">
              <svg className="w-10 h-10 mx-auto mb-2 text-sw-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5}
                  d="M7 16a4 4 0 01-.88-7.9A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <div className="font-medium text-slate-700">Arrastra un PDF aquí o haz clic para seleccionar</div>
              <div className="text-xs mt-1">Solo PDF con texto extraíble</div>
            </div>
          )}
        </div>

        {/* Lista de documentos */}
        <h2 className="text-sm font-semibold text-slate-600 uppercase tracking-wide mb-2">
          Documentos ingeridos ({docs.length})
        </h2>
        {docs.length === 0 ? (
          <div className="text-slate-400 text-sm">Aún no has subido documentos PDF.</div>
        ) : (
          <div className="space-y-2">
            {docs.map((d) => (
              <div key={d.doc_id} className="flex items-center gap-3 bg-white border border-sw-100 rounded-xl p-3">
                <div className="w-9 h-9 rounded-lg bg-red-50 text-red-500 flex items-center justify-center text-xs font-bold flex-shrink-0">
                  PDF
                </div>
                <div className="flex-1 min-w-0">
                  <div className="font-medium text-slate-700 truncate">{d.filename}</div>
                  <div className="text-xs text-slate-400">
                    {d.chunk_count} chunks · {d.char_count.toLocaleString()} caracteres · subido por {d.uploaded_by}
                  </div>
                </div>
                <button
                  onClick={() => handleDelete(d)}
                  className="text-slate-400 hover:text-red-500 p-2 rounded-lg hover:bg-red-50 transition-colors"
                  title="Eliminar de la base de conocimiento"
                >
                  <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6M1 7h22M9 7V4a1 1 0 011-1h4a1 1 0 011 1v3" />
                  </svg>
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
