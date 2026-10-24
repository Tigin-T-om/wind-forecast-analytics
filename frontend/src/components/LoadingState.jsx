export default function LoadingState({ message = 'Loading Wind Generation and Forecast Data...' }) {
  return (
    <div className="state-card loading-state" role="status" aria-live="polite">
      <div className="spinner-large" aria-hidden="true"></div>
      <h3 className="state-title">{message}</h3>
      <p className="state-subtitle">
        Querying official Elexon BMRS datasets (FUELHH actuals &amp; WINDFOR forecasts). This may take a moment for multi-day periods.
      </p>
    </div>
  )
}
