import { useState, useEffect } from 'react'
import DashboardHeader from './components/DashboardHeader'
import DateRangeFilter from './components/DateRangeFilter'
import MetricCard from './components/MetricCard'
import GenerationChart from './components/GenerationChart'
import ForecastErrorChart from './components/ForecastErrorChart'
import GenerationTable from './components/GenerationTable'
import LoadingState from './components/LoadingState'
import ErrorState from './components/ErrorState'
import { fetchAnalysis, fetchHealth } from './services/api'

export default function App() {
  const [filterParams, setFilterParams] = useState({
    startDate: '2026-01-01',
    endDate: '2026-01-31',
    cutoffPolicy: 'day_ahead_1700',
    resolution: 'hourly',
  })

  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [upstreamStatus, setUpstreamStatus] = useState('operational')

  // Probe backend and upstream health on mount
  useEffect(() => {
    let isMounted = true
    fetchHealth()
      .then((res) => {
        if (isMounted && res?.elexon_upstream) {
          setUpstreamStatus(res.elexon_upstream)
        }
      })
      .catch(() => {
        if (isMounted) setUpstreamStatus('unreachable')
      })
    return () => {
      isMounted = false
    }
  }, [])

  // Synchronize data with filter parameters
  useEffect(() => {
    let isCurrent = true
    async function loadData() {
      try {
        const result = await fetchAnalysis(filterParams)
        if (isCurrent) {
          setData(result)
          setError(null)
        }
      } catch (err) {
        if (isCurrent) {
          setError(err)
        }
      } finally {
        if (isCurrent) {
          setLoading(false)
        }
      }
    }

    loadData()

    return () => {
      isCurrent = false
    }
  }, [filterParams])

  const handleFilterApply = (newParams) => {
    setLoading(true)
    setError(null)
    setFilterParams(newParams)
  }

  const handleRetry = () => {
    setLoading(true)
    setError(null)
    setFilterParams((prev) => ({ ...prev }))
  }

  const metrics = data?.summary_metrics
  const policy = data?.forecast_selection_policy
  const observations = data?.observations || []

  // Bias badge formatting
  let biasBadge = 'Balanced'
  let biasVariant = 'neutral'
  if (metrics?.bias !== null && metrics?.bias !== undefined) {
    if (metrics.bias > 50) {
      biasBadge = 'Overforecasting (+)'
      biasVariant = 'warning'
    } else if (metrics.bias < -50) {
      biasBadge = 'Underforecasting (−)'
      biasVariant = 'info'
    }
  }

  return (
    <div className="dashboard-layout">
      <DashboardHeader
        upstreamStatus={upstreamStatus}
        isCached={data?.retrieval_status?.cached}
        timezone={data?.timezone_convention || 'UTC'}
      />

      <main className="dashboard-content">
        <DateRangeFilter
          startDate={filterParams.startDate}
          endDate={filterParams.endDate}
          cutoffPolicy={filterParams.cutoffPolicy}
          resolution={filterParams.resolution}
          onApply={handleFilterApply}
          isLoading={loading}
        />

        {loading && <LoadingState />}

        {error && !loading && (
          <ErrorState error={error} onRetry={handleRetry} />
        )}

        {!loading && !error && data && (
          <>
            {/* Policy & Resolution Provenance Banner */}
            <div className="policy-banner">
              <div className="policy-info">
                <span className="policy-tag">Active Cutoff Policy:</span>
                <strong className="policy-name">{policy?.name}</strong>
                <span className="policy-rule">({policy?.cutoff_rule})</span>
              </div>
              <div className="policy-desc">
                <strong>Resolution Mode:</strong> {metrics?.resolution_description}
              </div>
            </div>

            {/* Warnings banner if any */}
            {data.retrieval_status?.warnings?.length > 0 && (
              <div className="warning-banner" role="status">
                {data.retrieval_status.warnings.map((w, i) => (
                  <p key={i}>{w}</p>
                ))}
              </div>
            )}

            {/* Executive Summary Metrics Grid */}
            <section className="metrics-grid" aria-label="Summary Metrics">
              <MetricCard
                title="Mean Absolute Error (MAE)"
                value={metrics?.mae}
                unit="MW"
                description="Average absolute magnitude of forecast deviations across all matched intervals."
                badgeText="Standard Accuracy"
                badgeVariant="neutral"
              />

              <MetricCard
                title="Root Mean Squared Error (RMSE)"
                value={metrics?.rmse}
                unit="MW"
                description="Quadratic penalty scoring prioritizing volatility and large deviations."
                badgeText="Volatility Penalty"
                badgeVariant="neutral"
              />

              <MetricCard
                title="Forecast Bias (Mean Error)"
                value={metrics?.bias}
                type="signed"
                unit="MW"
                description="Signed variance (Forecast − Actual). Positive indicates systemic overforecast."
                badgeText={biasBadge}
                badgeVariant={biasVariant}
              />

              <MetricCard
                title="Matched Observations"
                value={metrics?.matched_count}
                type="count"
                unit={`/ ${metrics?.total_expected_intervals || 0}`}
                description={`Evaluated ${metrics?.matched_count || 0} intervals using ${metrics?.total_actual_records_used || 0} metered actual half-hours (${metrics?.coverage_percentage || 0}% coverage).`}
                badgeText={`${metrics?.coverage_percentage || 0}% Coverage`}
                badgeVariant="success"
              />
            </section>

            {/* Visual Analytics */}
            <section className="analytics-section">
              <GenerationChart observations={observations} />
              <ForecastErrorChart observations={observations} />
            </section>

            {/* Detailed Data Table */}
            <section className="table-section">
              <GenerationTable observations={observations} />
            </section>

            {/* Data Provenance & Methodology Reference */}
            <section className="provenance-card">
              <h3 className="provenance-title">Methodology &amp; Data Provenance</h3>
              <div className="provenance-grid">
                <div>
                  <h4>Official Elexon Streams &amp; Resolutions</h4>
                  <p>
                    <strong>Actual Generation (FUELHH):</strong> Official half-hourly metered generation stream for fuelType = WIND. Each standard day comprises 48 settlement periods.
                  </p>
                  <p>
                    <strong>Forecast Generation (WINDFOR):</strong> Official hourly Day-Ahead national wind forecast stream published by National Grid ESO (24 intervals per day).
                  </p>
                  <p>
                    <strong>Hourly Energy-Weighted Averaging:</strong> To rigorously compare hourly forecasts against half-hourly actuals without discarding data, each hour averages both 30-minute actual settlement periods (<code>(SP1 + SP2) / 2</code>). This incorporates 100% of metered generation data.
                  </p>
                </div>
                <div>
                  <h4>Forecast Cutoff &amp; Market Rules</h4>
                  <p>
                    Under UK Day-Ahead power purchasing, transactions clear prior to the delivery day. The <strong>Day-Ahead 17:00 UTC (D-1)</strong> policy enforces that no forecast published after 17:00 on the day prior to delivery can be selected, eliminating look-ahead bias.
                  </p>
                  <p>
                    <strong>Sign Conventions:</strong> Signed Error = Forecast − Actual. Positive bias signifies overforecasting (purchased more wind energy than was actually generated, leading to imbalance system sell charges).
                  </p>
                </div>
              </div>
            </section>
          </>
        )}
      </main>

      <footer className="dashboard-footer">
        <p>
          Wind Forecast Analytics &copy; 2026. Data sourced from Elexon BMRS API. Strictly non-commercial evaluation build.
        </p>
      </footer>
    </div>
  )
}
