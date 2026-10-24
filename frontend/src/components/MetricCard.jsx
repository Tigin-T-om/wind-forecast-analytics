import { formatMW, formatSignedMW } from '../utils/formatters'

export default function MetricCard({
  title,
  value,
  type = 'standard', // 'standard', 'signed', 'count'
  unit = 'MW',
  decimals = 0,
  description,
  trend,
  badgeText,
  badgeVariant = 'neutral',
}) {
  let displayValue = '—'
  if (value !== null && value !== undefined) {
    if (type === 'signed') {
      displayValue = formatSignedMW(value, decimals)
    } else if (type === 'count') {
      displayValue = Number(value).toLocaleString('en-GB')
    } else {
      displayValue = formatMW(value, decimals)
    }
  }

  return (
    <div className={`metric-card metric-card-${badgeVariant}`}>
      <div className="metric-header">
        <span className="metric-title">{title}</span>
        {badgeText && (
          <span className={`metric-badge badge-${badgeVariant}`}>
            {badgeText}
          </span>
        )}
      </div>

      <div className="metric-value-container">
        <span className="metric-value">{displayValue}</span>
        {type === 'count' && unit && <span className="metric-unit">{unit}</span>}
      </div>

      {description && <p className="metric-description">{description}</p>}
      {trend && <div className="metric-trend">{trend}</div>}
    </div>
  )
}
