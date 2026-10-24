import { useState, useRef, useMemo, useCallback } from 'react'
import { formatMW, formatSignedMW, formatDateTimeUTC, formatShortDateUTC } from '../utils/formatters'

export default function GenerationChart({ observations = [] }) {
  const containerRef = useRef(null)
  const [hoveredIndex, setHoveredIndex] = useState(null)
  const [filterMode, setFilterMode] = useState('all') // 'all' or 'matched_only'

  // Filter observations if requested
  const chartData = useMemo(() => {
    if (filterMode === 'matched_only') {
      return observations.filter((d) => d.status === 'matched')
    }
    return observations
  }, [observations, filterMode])

  // Calculate scales and bounds
  const { maxVal, minVal, yTicks } = useMemo(() => {
    let max = 1000
    let min = 0
    chartData.forEach((d) => {
      if (d.actual_mw !== null && d.actual_mw > max) max = d.actual_mw
      if (d.forecast_mw !== null && d.forecast_mw > max) max = d.forecast_mw
    })
    // Add 10% headroom
    const roundedMax = Math.ceil((max * 1.1) / 2000) * 2000
    const ticks = []
    const step = roundedMax / 5
    for (let i = 0; i <= 5; i++) {
      ticks.push(Math.round(step * i))
    }
    return { maxVal: roundedMax, minVal: min, yTicks: ticks }
  }, [chartData])

  // Chart dimensions
  const width = 1000
  const height = 400
  const margin = { top: 20, right: 30, bottom: 45, left: 75 }
  const innerWidth = width - margin.left - margin.right
  const innerHeight = height - margin.top - margin.bottom

  const n = chartData.length

  // Coordinate mappers
  const getX = useCallback(
    (index) => {
      if (n <= 1) return margin.left + innerWidth / 2
      return margin.left + (index / (n - 1)) * innerWidth
    },
    [n, margin.left, innerWidth]
  )

  const getY = useCallback(
    (val) => {
      if (val === null || val === undefined || isNaN(val)) return null
      const clamped = Math.max(minVal, Math.min(maxVal, val))
      return margin.top + innerHeight - ((clamped - minVal) / (maxVal - minVal)) * innerHeight
    },
    [minVal, maxVal, margin.top, innerHeight]
  )

  // Generate SVG path segments (respecting gaps for nulls)
  const generatePath = useCallback(
    (key) => {
      const segments = []
      let currentSegment = []

      chartData.forEach((d, idx) => {
        const val = d[key]
        if (val !== null && val !== undefined) {
          currentSegment.push([getX(idx), getY(val)])
        } else {
          if (currentSegment.length > 0) {
            segments.push(currentSegment)
            currentSegment = []
          }
        }
      })
      if (currentSegment.length > 0) {
        segments.push(currentSegment)
      }

      return segments
        .map((segment) => {
          if (segment.length === 0) return ''
          return segment
            .map((pt, i) => `${i === 0 ? 'M' : 'L'} ${pt[0].toFixed(1)} ${pt[1].toFixed(1)}`)
            .join(' ')
        })
        .filter(Boolean)
    },
    [chartData, getX, getY]
  )

  const actualPaths = useMemo(() => generatePath('actual_mw'), [generatePath])
  const forecastPaths = useMemo(() => generatePath('forecast_mw'), [generatePath])

  // X-axis ticks (sample 6-8 evenly spaced ticks)
  const xTicks = useMemo(() => {
    if (n === 0) return []
    const tickCount = Math.min(7, n)
    const step = Math.floor(n / (tickCount - 1)) || 1
    const ticks = []
    for (let i = 0; i < n; i += step) {
      ticks.push({ index: i, obs: chartData[i] })
    }
    // Ensure last item is included
    if (ticks[ticks.length - 1].index !== n - 1) {
      ticks.push({ index: n - 1, obs: chartData[n - 1] })
    }
    return ticks
  }, [chartData, n])

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

  const activeObs = hoveredIndex !== null && chartData[hoveredIndex] ? chartData[hoveredIndex] : null
  const activeX = hoveredIndex !== null ? getX(hoveredIndex) : null

  return (
    <div className="chart-card">
      <div className="chart-header">
        <div>
          <h2 className="chart-title">Actual vs Forecast Wind Generation</h2>
          <p className="chart-subtitle">
            National metered generation (FUELHH) compared to Day-Ahead wind forecast (WINDFOR) in MW
          </p>
        </div>

        <div className="chart-controls">
          <div className="chart-legend">
            <span className="legend-item">
              <span className="legend-indicator legend-actual"></span>
              Actual Generation
            </span>
            <span className="legend-item">
              <span className="legend-indicator legend-forecast"></span>
              Day-Ahead Forecast
            </span>
          </div>

          <div className="chart-filter-toggle">
            <button
              type="button"
              className={`toggle-btn ${filterMode === 'all' ? 'active' : ''}`}
              onClick={() => setFilterMode('all')}
            >
              All Intervals
            </button>
            <button
              type="button"
              className={`toggle-btn ${filterMode === 'matched_only' ? 'active' : ''}`}
              onClick={() => setFilterMode('matched_only')}
            >
              Matched Only
            </button>
          </div>
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
          aria-label="Line chart comparing actual wind generation and forecast generation"
        >
          {/* Horizontal grid lines */}
          {yTicks.map((tick) => {
            const y = getY(tick)
            return (
              <g key={`y-grid-${tick}`}>
                <line
                  x1={margin.left}
                  y1={y}
                  x2={width - margin.right}
                  y2={y}
                  className="chart-grid-line"
                />
                <text
                  x={margin.left - 12}
                  y={y + 4}
                  className="chart-axis-label"
                  textAnchor="end"
                >
                  {tick.toLocaleString('en-GB')} MW
                </text>
              </g>
            )
          })}

          {/* X Axis line */}
          <line
            x1={margin.left}
            y1={margin.top + innerHeight}
            x2={width - margin.right}
            y2={margin.top + innerHeight}
            className="chart-axis-line"
          />

          {/* X-axis date ticks */}
          {xTicks.map((tick) => {
            const x = getX(tick.index)
            return (
              <g key={`x-tick-${tick.index}`}>
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

          {/* Actual Generation Line */}
          {actualPaths.map((dStr, idx) => (
            <path
              key={`actual-${idx}`}
              d={dStr}
              fill="none"
              className="line-actual"
              strokeWidth="2.2"
            />
          ))}

          {/* Forecast Generation Line */}
          {forecastPaths.map((dStr, idx) => (
            <path
              key={`forecast-${idx}`}
              d={dStr}
              fill="none"
              className="line-forecast"
              strokeWidth="2.2"
              strokeDasharray="4 2"
            />
          ))}

          {/* Active Hover Guideline and Dots */}
          {activeObs && activeX !== null && (
            <g className="chart-hover-overlay">
              <line
                x1={activeX}
                y1={margin.top}
                x2={activeX}
                y2={margin.top + innerHeight}
                className="chart-crosshair"
              />
              {activeObs.actual_mw !== null && (
                <circle
                  cx={activeX}
                  cy={getY(activeObs.actual_mw)}
                  r="5"
                  className="point-actual"
                />
              )}
              {activeObs.forecast_mw !== null && (
                <circle
                  cx={activeX}
                  cy={getY(activeObs.forecast_mw)}
                  r="5"
                  className="point-forecast"
                />
              )}
            </g>
          )}
        </svg>

        {/* Hover Tooltip */}
        {activeObs && (
          <div
            className="chart-tooltip"
            style={{
              left: `${Math.min(80, Math.max(15, (activeX / width) * 100))}%`,
              top: '12%',
            }}
          >
            <div className="tooltip-title">
              {formatDateTimeUTC(activeObs.delivery_timestamp)}
            </div>
            <div className="tooltip-row">
              <span className="tooltip-indicator indicator-actual"></span>
              <span className="tooltip-label">Actual:</span>
              <span className="tooltip-value font-mono">
                {formatMW(activeObs.actual_mw)}
              </span>
            </div>
            <div className="tooltip-row">
              <span className="tooltip-indicator indicator-forecast"></span>
              <span className="tooltip-label">Forecast:</span>
              <span className="tooltip-value font-mono">
                {formatMW(activeObs.forecast_mw)}
              </span>
            </div>
            {activeObs.signed_error !== null && (
              <div className="tooltip-row tooltip-error-row">
                <span className="tooltip-label">Variance (F - A):</span>
                <span
                  className={`tooltip-value font-mono ${
                    activeObs.signed_error > 0 ? 'error-positive' : 'error-negative'
                  }`}
                >
                  {formatSignedMW(activeObs.signed_error)}
                </span>
              </div>
            )}
            {activeObs.status !== 'matched' && (
              <div className="tooltip-status-note">
                Status: {activeObs.status === 'missing_forecast' ? 'No forecast before cutoff' : 'Missing actual meter'}
              </div>
            )}
          </div>
        )}
      </div>

      <div className="chart-footer-note">
        <span>Delivery interval start time in UTC. Missing intervals are represented as discontinuous segments (never false zeroes).</span>
      </div>
    </div>
  )
}
