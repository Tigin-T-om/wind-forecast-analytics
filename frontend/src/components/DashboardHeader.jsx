export default function DashboardHeader({ upstreamStatus, isCached, timezone = 'UTC' }) {
  return (
    <header className="dashboard-header">
      <div className="header-brand-container">
        <div className="header-title-row">
          <div className="brand-icon-wrapper" aria-hidden="true">
            <svg width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M9.59 4.59A2 2 0 1 1 11 8H2m10.59 11.41A2 2 0 1 0 14 16H2m15.73-8.27A2.5 2.5 0 1 1 19.5 12H2" />
            </svg>
          </div>
          <div>
            <h1 className="header-title">Wind Forecast Analytics</h1>
            <p className="header-subtitle">
              UK National Wind Generation &amp; Day-Ahead Forecast Accuracy Dashboard
            </p>
          </div>
        </div>

        <div className="header-meta-row">
          <div className="meta-badge" title="Data is processed and displayed in Coordinated Universal Time">
            <span className="meta-label">Timezone:</span>
            <span className="meta-value">{timezone}</span>
          </div>

          <div className="meta-badge" title="Official national datasets from Elexon BSC Portal">
            <span className="meta-label">Source:</span>
            <span className="meta-value">Elexon BMRS (FUELHH &amp; WINDFOR)</span>
          </div>

          <div className="meta-badge">
            <span className="meta-label">Upstream:</span>
            <span className={`status-indicator ${upstreamStatus === 'operational' ? 'status-online' : 'status-pending'}`}>
              <span className="status-dot"></span>
              {upstreamStatus === 'operational' ? 'Live Operational' : 'Verifying...'}
            </span>
          </div>

          {isCached && (
            <div className="meta-badge cache-badge" title="Data retrieved from local in-memory cache">
              <span className="meta-value">Cached (Fast)</span>
            </div>
          )}
        </div>
      </div>
    </header>
  )
}
