import { useState } from 'react'

const POLICY_OPTIONS = [
  {
    id: 'day_ahead_1200',
    label: 'Day-Ahead 12:00 UTC (D-1) — Auction Cutoff',
    title: 'EPEX SPOT auction deadline: forecasts published strictly on or before 12:00 UTC on the prior day (D-1)',
  },
  {
    id: 'day_ahead_1700',
    label: 'Day-Ahead 17:00 UTC (D-1) — Gate Closure',
    title: 'Physical notification gate: forecasts published strictly on or before 17:00 UTC on the prior day (D-1)',
  },
  {
    id: 'gate_closure_1h',
    label: 'Gate Closure (1h Prior) — Operational Balancing',
    title: 'Balancing Mechanism gate: forecasts published at least 1 hour before delivery interval start',
  },
  {
    id: 'latest_prior',
    label: 'Latest Prior to Delivery — Within-Day / Intraday',
    title: 'Intraday updates: latest forecast published strictly prior to delivery start',
  },
]

const RESOLUTION_OPTIONS = [
  { id: 'hourly', label: 'Hourly Energy Average (100% Coverage — Recommended)' },
  { id: 'half_hourly', label: 'Half-Hourly Settlement Periods (100% Coverage)' },
  { id: 'exact', label: 'Exact Delivery Timestamp (:00 only — 50% Coverage)' },
]

export default function DateRangeFilter({
  startDate,
  endDate,
  cutoffPolicy,
  resolution = 'hourly',
  onApply,
  isLoading,
}) {
  const [localStart, setLocalStart] = useState(startDate)
  const [localEnd, setLocalEnd] = useState(endDate)
  const [validationError, setValidationError] = useState('')

  const handlePolicyChange = (newPolicy) => {
    onApply({
      startDate: localStart,
      endDate: localEnd,
      cutoffPolicy: newPolicy,
      resolution,
    })
  }

  const handleResolutionChange = (newRes) => {
    onApply({
      startDate: localStart,
      endDate: localEnd,
      cutoffPolicy,
      resolution: newRes,
    })
  }

  const handlePreset = (start, end) => {
    setLocalStart(start)
    setLocalEnd(end)
    setValidationError('')
    onApply({
      startDate: start,
      endDate: end,
      cutoffPolicy,
      resolution,
    })
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!localStart || !localEnd) {
      setValidationError('Both start and end dates are required.')
      return
    }
    if (localStart > localEnd) {
      setValidationError('Start date cannot be after end date.')
      return
    }
    setValidationError('')
    onApply({
      startDate: localStart,
      endDate: localEnd,
      cutoffPolicy,
      resolution,
    })
  }

  return (
    <div className="filter-card">
      <form onSubmit={handleSubmit} className="filter-form">
        <div className="filter-controls-grid">
          <div className="filter-group">
            <label htmlFor="filter-start-date" className="filter-label">
              Start Date (UTC)
            </label>
            <input
              id="filter-start-date"
              type="date"
              className="filter-input"
              value={localStart}
              onChange={(e) => setLocalStart(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="filter-group">
            <label htmlFor="filter-end-date" className="filter-label">
              End Date (UTC)
            </label>
            <input
              id="filter-end-date"
              type="date"
              className="filter-input"
              value={localEnd}
              onChange={(e) => setLocalEnd(e.target.value)}
              disabled={isLoading}
            />
          </div>

          <div className="filter-group policy-group">
            <label htmlFor="filter-policy" className="filter-label">
              Forecast Cutoff Policy
            </label>
            <select
              id="filter-policy"
              className="filter-select"
              value={cutoffPolicy}
              onChange={(e) => handlePolicyChange(e.target.value)}
              disabled={isLoading}
            >
              {POLICY_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id} title={opt.title}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-group resolution-group">
            <label htmlFor="filter-resolution" className="filter-label">
              Comparison Resolution
            </label>
            <select
              id="filter-resolution"
              className="filter-select"
              value={resolution}
              onChange={(e) => handleResolutionChange(e.target.value)}
              disabled={isLoading}
            >
              {RESOLUTION_OPTIONS.map((opt) => (
                <option key={opt.id} value={opt.id}>
                  {opt.label}
                </option>
              ))}
            </select>
          </div>

          <div className="filter-actions">
            <button
              id="btn-apply-filter"
              type="submit"
              className="btn btn-primary"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <span className="spinner-inline" aria-hidden="true"></span>
                  Processing...
                </>
              ) : (
                'Update Analysis'
              )}
            </button>
          </div>
        </div>

        {validationError && (
          <div className="filter-validation-error" role="alert">
            {validationError}
          </div>
        )}

        <div className="filter-presets">
          <span className="preset-label">January 2026 Presets:</span>
          <button
            type="button"
            className={`preset-chip ${localStart === '2026-01-01' && localEnd === '2026-01-31' ? 'active' : ''}`}
            onClick={() => handlePreset('2026-01-01', '2026-01-31')}
            disabled={isLoading}
          >
            Full Month (Jan 1–31)
          </button>
          <button
            type="button"
            className={`preset-chip ${localStart === '2026-01-01' && localEnd === '2026-01-07' ? 'active' : ''}`}
            onClick={() => handlePreset('2026-01-01', '2026-01-07')}
            disabled={isLoading}
          >
            Week 1 (Jan 1–7)
          </button>
          <button
            type="button"
            className={`preset-chip ${localStart === '2026-01-08' && localEnd === '2026-01-14' ? 'active' : ''}`}
            onClick={() => handlePreset('2026-01-08', '2026-01-14')}
            disabled={isLoading}
          >
            Week 2 (Jan 8–14)
          </button>
          <button
            type="button"
            className={`preset-chip ${localStart === '2026-01-15' && localEnd === '2026-01-21' ? 'active' : ''}`}
            onClick={() => handlePreset('2026-01-15', '2026-01-21')}
            disabled={isLoading}
          >
            Week 3 (Jan 15–21)
          </button>
          <button
            type="button"
            className={`preset-chip ${localStart === '2026-01-22' && localEnd === '2026-01-31' ? 'active' : ''}`}
            onClick={() => handlePreset('2026-01-22', '2026-01-31')}
            disabled={isLoading}
          >
            Week 4 (Jan 22–31)
          </button>
        </div>
      </form>
    </div>
  )
}
