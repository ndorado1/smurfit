/**
 * Placeholders animados que se muestran mientras se cargan los mensajes
 * de una conversacion. Imita la silueta de una burbuja de usuario y una
 * de asistente para que la transicion sea visualmente continua.
 */
function SkeletonBubble({ side = 'left', width = 'w-2/3' }) {
  const isLeft = side === 'left'
  return (
    <div className={`flex ${isLeft ? 'justify-start' : 'justify-end'} mb-4 gap-3`}>
      {isLeft && <div className="w-8 h-8 rounded-full bg-slate-200 flex-shrink-0 mt-1 animate-pulse" />}
      <div className={`${width} max-w-[75%]`}>
        <div className={`rounded-2xl ${isLeft ? 'rounded-tl-sm bg-sw-50' : 'rounded-tr-sm bg-sw-100'} p-3 space-y-2`}>
          <div className="h-3 bg-slate-200 rounded animate-pulse w-11/12" />
          <div className="h-3 bg-slate-200 rounded animate-pulse w-9/12" />
          {isLeft && <div className="h-3 bg-slate-200 rounded animate-pulse w-10/12" />}
        </div>
      </div>
      {!isLeft && <div className="w-8 h-8 rounded-full bg-slate-200 flex-shrink-0 mt-1 animate-pulse" />}
    </div>
  )
}

export default function MessageSkeleton() {
  return (
    <div>
      <SkeletonBubble side="right" width="w-1/2" />
      <SkeletonBubble side="left"  width="w-2/3" />
      <SkeletonBubble side="right" width="w-2/5" />
      <SkeletonBubble side="left"  width="w-3/4" />
    </div>
  )
}
