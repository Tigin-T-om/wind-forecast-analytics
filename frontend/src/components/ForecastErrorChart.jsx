import { useState, useRef, useMemo } from 'react'
import { formatSignedMW, formatDateTimeUTC, formatShortDateUTC } from '../utils/formatters'

export default function ForecastErrorChart({ observations = [] }) {
  const containerRef = useRef(null)
  const [hoveredIndex, setHoveredIndex] = useState(null)

  // Filter strictly to matched observations where signed_error is valid
  const errorData = useMemo(() => {
    return observations.filter((d) => d.status === 'matched' && d.signed_error !== null)
  }, [observations])

  const n = errorData.length

  // Calculate dynamic symmetric Y-bounds around 0 MW
  const { maxAbsError, yTicks } = useMemo(() => {
    let maxAbs = 500
    errorData.forEach((d) => {
      const absVal = Math.abs(d.signed_error)
      if (absVal > maxAbs) maxAbs = absVal
    })
    // Round to nearest 1000
    const roundedMax = Math.ceil((maxAbs * 1.15) / 1000) * 1000
    const ticks = [-roundedMax, -roundedMax / 2, 0, roundedMax / 2, roundedMax]
    return { maxAbsError: roundedMax, yTicks: ticks }
  }, [errorData])

  const width = 1000
  const height = 260
  const margin = { top: 20, right: 30, bottom: 40, left: 75 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom

  const getX = (index) => {
    if (n <= 1) return margin.left + innerWidth / 2
    return margin.left + (index / (n - 1)) * innerWidth
  }

  const getY = (val) => {
    const clamped = Math.max(-maxAbsError, Math.min(maxAbsError, val))
    // Zero is in the middle of innerHeight
    return margin.top + innerHeight / 2 - (clamped / maxAbsError) * (innerHeight / 2)
  }

  const zeroY = getY(0)

  // X ticks
  const xTicks = useMemo(() => {
    if (n === 0) return []
    const tickCount = Math.min(7, n)
    const step = Math.floor(n / (tickCount - 1)) || 1
    const ticks = []
    for (let i = 0; i < n; i += step) {
      ticks.push({ index: i, obs: errorData[i] })
    }
    if (ticks[ticks.length - 1].index !== n - 1) {
      ticks.push({ index: n - 1, obs: errorData[n - 1] })
    }
    return ticks
  }, [errorData, n])

  const handleMouseMove = (e) => {
    if (!containerRef.current || n === 0) return
    const rect = containerRef.current.getBoundingClientRect()
    const mouseX = e.clientX - rect.left
    const svgX = (mouseX / rect.width) * width
    const relativeX = svgX - margin.left
    const ratio = Math.max(0, Math.min(1, relativeX / innerWidth))
    const index = Math.round(ratio * (n - 1))
    setHoveredIndex(index)
  }

  const handleMouseLeave = () => {
    setHoveredIndex(null)
  }

  const activeObs = hoveredIndex !== null && errorData[hoveredIndex] ? errorData[hoveredIndex] : null
  const activeX = hoveredIndex !== null ? getX(hoveredIndex) : null

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <h2 className="chart-title">Forecast Error Distribution (Signed Bias)</h2>
          <p className="chart-subtitle">
            Signed variance (Forecast − Actual) over delivery intervals in MW
          </p>
        </div>

        <div className="chart-legend">
          <span className="legend-item">
            <span className="legend-indicator legend-overforecast"></span>
            Overforecast (+MW)
          </span>
          <span className="legend-item">
            <span className="legend-indicator legend-underforecast"></span>
            Underforecast (−MW)
          </span>
        </div>
      </div>

      <div
        className="chart-svg-container"
        ref={containerRef}
        onMouseMove={handleMouseMove}
        onMouseLeave={handleMouseLeave}
      >
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="chart-svg"
          preserveAspectRatio="none"
          role="img"
          aria-label="Area chart showing signed wind forecast errors over time"
        >
          {/* Horizontal grid lines */}
          {yTicks.map((tick) => {
            const y = getY(tick)
            return (
              <g key={`y-error-${tick}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={width - margin.right}
                  y2={y}
                  className={tick === 0 ? 'chart-zero-line' : 'chart-grid-line'}
                />
                <text
                  x={margin.left - 12}
                  y={y + 4}
                  className="chart-axis-label"
                  textAnchor="end"
                >
                  {tick > 0 ? `+${tick.toLocaleString('en-GB')}` : tick.toLocaleString('en-GB')} MW
                </text>
              </g>
            )
          })}

          {/* X-axis date ticks */}
          {xTicks.map((tick) => {
            const x = getX(tick.index)
            return (
              <g key={`x-err-tick-${tick.index}`}>
                <line
                  x1={x}
                  y1={margin.top + innerHeight}
                  x2={x}
                  y2={margin.top + innerHeight + 6}
                  className="chart-axis-tick"
                />
                <text
                  x={x}
                  y={margin.top + innerHeight + 20}
                  className="chart-axis-label"
                  textAnchor="middle"
                >
                  {formatShortDateUTC(tick.obs.delivery_timestamp)}
                </text>
              </g>
            )
          })}

          {/* Error Bars / Stems */}
          {errorData.map((d, idx) => {
            const x = getX(idx)
            const y = getY(d.signed_error)
            const isPositive = d.signed_error >= 0
            const barWidth = Math.max(2, Math.min(8, (innerWidth / n) * 0.7))

            return (
              <rect
                key={`err-bar-${idx}`}
                x={x - barWidth / 2}
                y={isPositive ? y : zeroY}
                width={barWidth}
                height={Math.max(1, Math.abs(y - zeroY))}
                className={isPositive ? 'bar-overforecast' : 'bar-underforecast'}
                rx="1"
              />
            )
          })}

          {/* Zero baseline highlight */}
          <line
            x1={margin.left}
            y1={zeroY}
            x2={width - margin.right}
            y2={zeroY}
            className="chart-zero-line-accent"
          />

          {/* Active Hover Crosshair */}
          {activeObs && activeX !== null && (
            <g className="chart-hover-overlay">
              <line
                x1={activeX}
                y1={margin.top}
                x2={activeX}
                y2={margin.top + innerHeight}
                className="chart-crosshair"
              />
              <circle
                cx={activeX}
                cy={getY(activeObs.signed_error)}
                r="5"
                className={
                  activeObs.signed_error >= 0 ? 'point-overforecast' : 'point-underforecast'
                }
              />
            </g>
          )}
        </svg>

        {/* Hover Tooltip */}
        {activeObs && (
          <div
            className="chart-tooltip"
            style={{
              left: `${Math.min(80, Math.max(15, (activeX / width) * 100))}%`,
              top: '15%',
            }}
          >
            <div className="tooltip-title">
              {formatDateTimeUTC(activeObs.delivery_timestamp)}
            </div>
            <div className="tooltip-row">
              <span className="tooltip-label">Signed Error:</span>
              <span
                className={`tooltip-value font-mono ${
                  activeObs.signed_error > 0 ? 'error-positive' : 'error-negative'
                }`}
              >
                {formatSignedMW(activeObs.signed_error)}
              </span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-label">Absolute Error:</span>
              <span className="tooltip-value font-mono">
                {formatSignedMW(activeObs.absolute_error)}
              </span>
            </div>
            <div className="tooltip-status-note">
              {activeObs.signed_error > 0
                ? 'Forecast OVERESTIMATED actual wind generation'
                : 'Forecast UNDERESTIMATED actual wind generation'}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
