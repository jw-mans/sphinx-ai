import type { CompetencyProfile } from '../api/interview'

interface Props {
  profile: CompetencyProfile
}

const AXES: { key: keyof CompetencyProfile['dimensions']; label: string }[] = [
  { key: 'correctness', label: 'Правильность' },
  { key: 'optimality',  label: 'Оптимальность' },
  { key: 'complexity',  label: 'Сложность' },
  { key: 'explanation', label: 'Объяснение' },
  { key: 'gaps',        label: 'Пробелы' },
]

const N      = AXES.length
const CX     = 160
const CY     = 160
const R      = 110          // outer radius of chart area
const LEVELS = [0.25, 0.5, 0.75, 1.0]

function polar(angle: number, r: number) {
  return { x: CX + r * Math.cos(angle), y: CY + r * Math.sin(angle) }
}

const angles = AXES.map((_, i) => (2 * Math.PI * i) / N - Math.PI / 2)

function makePolygon(values: number[]): string {
  return values
    .map((v, i) => {
      const pt = polar(angles[i], (v / 10) * R)
      return `${pt.x},${pt.y}`
    })
    .join(' ')
}

function makeGridPolygon(frac: number): string {
  return angles
    .map(a => {
      const pt = polar(a, frac * R)
      return `${pt.x},${pt.y}`
    })
    .join(' ')
}

export function CompetencyMap({ profile }: Props) {
  const values = AXES.map(a => profile.dimensions[a.key] ?? 0)

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 flex flex-col gap-4">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-slate-300">Карта компетенций</h2>
        <span className="text-xs text-slate-500">
          {profile.interviews_count} интервью · {profile.evaluated_answers} ответов
        </span>
      </div>

      <svg viewBox="0 0 320 320" className="w-full max-w-xs mx-auto select-none">
        {/* Grid polygons */}
        {LEVELS.map(frac => (
          <polygon
            key={frac}
            points={makeGridPolygon(frac)}
            fill="none"
            stroke="#334155"
            strokeWidth="1"
          />
        ))}

        {/* Axis lines */}
        {angles.map((angle, i) => {
          const end = polar(angle, R)
          return (
            <line
              key={i}
              x1={CX} y1={CY}
              x2={end.x} y2={end.y}
              stroke="#334155"
              strokeWidth="1"
            />
          )
        })}

        {/* Value polygon — filled area */}
        <polygon
          points={makePolygon(values)}
          fill="rgba(99,102,241,0.15)"
          stroke="#6366f1"
          strokeWidth="2"
          strokeLinejoin="round"
        />

        {/* Value dots */}
        {values.map((v, i) => {
          const pt = polar(angles[i], (v / 10) * R)
          return (
            <circle
              key={i}
              cx={pt.x} cy={pt.y}
              r="4"
              fill="#6366f1"
              stroke="#1e293b"
              strokeWidth="1.5"
            />
          )
        })}

        {/* Axis labels */}
        {AXES.map((axis, i) => {
          const labelR = R + 22
          const pt     = polar(angles[i], labelR)
          const anchor =
            Math.abs(pt.x - CX) < 5 ? 'middle'
            : pt.x < CX            ? 'end'
            :                        'start'
          return (
            <text
              key={axis.key}
              x={pt.x} y={pt.y + 4}
              textAnchor={anchor}
              fontSize="11"
              fill="#94a3b8"
              fontFamily="inherit"
            >
              {axis.label}
            </text>
          )
        })}

        {/* Value labels on dots */}
        {values.map((v, i) => {
          const pt     = polar(angles[i], (v / 10) * R)
          const offsetX = pt.x < CX ? -8 : pt.x > CX + 5 ? 8 : 0
          const offsetY = pt.y < CY ? -8 : 12
          return (
            <text
              key={i}
              x={pt.x + offsetX} y={pt.y + offsetY}
              textAnchor="middle"
              fontSize="10"
              fill="#e2e8f0"
              fontWeight="600"
              fontFamily="inherit"
            >
              {v.toFixed(1)}
            </text>
          )
        })}
      </svg>

      {/* Weak topics */}
      {profile.weak_topics.length > 0 && (
        <div>
          <p className="text-xs font-semibold text-rose-400 mb-2">Слабые темы (топ)</p>
          <div className="flex flex-wrap gap-1">
            {profile.weak_topics.map(t => (
              <span
                key={t}
                className="text-xs px-2 py-0.5 rounded bg-rose-500/10 border border-rose-500/20 text-rose-400"
              >
                {t}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
