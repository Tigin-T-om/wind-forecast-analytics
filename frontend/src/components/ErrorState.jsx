export default function ErrorState({ error, onRetry }) {
  const errorMessage = error?.message || (typeof error === 'string' ? error : 'An unexpected error occurred.')

  return (
    <div className="state-card error-state" role="alert">
      <div className="error-icon" aria-hidden="true">
        <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="12" cy="12" r="10" />
          <line x1="12" y1="8" x2="12" y2="12" />
          <line x1="12" y1="16" x2="12.01" y2="16" />
        </svg>
      </div>
      <h3 className="state-title">Analysis Data Unavailable</h3>
      <p className="state-subtitle">{errorMessage}</p>

      {onRetry && (
        <div className="error-actions">
          <button type="button" className="btn btn-primary" onClick={onRetry}>
            Retry Request
          </button>
        </div>
      )}
    </div>
  )
}
