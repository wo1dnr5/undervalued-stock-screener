export default function ScoreBar({ score }: { score: number }) {
  const color =
    score >= 70 ? 'bg-emerald-500' :
    score >= 50 ? 'bg-blue-500' :
    score >= 30 ? 'bg-amber-400' : 'bg-red-400'

  return (
    <div className="flex items-center gap-2.5">
      <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full ${color} transition-all duration-300`}
          style={{ width: `${score}%` }}
        />
      </div>
      <span className="text-xs font-semibold text-gray-600 w-7 text-right tabular-nums">
        {score.toFixed(0)}
      </span>
    </div>
  )
}
