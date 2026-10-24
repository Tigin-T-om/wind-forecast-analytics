/**
 * Utilities for formatting electricity data, MW units, timestamps, and status badges.
 */

export function formatMW(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) {
    return '—'
  }
  const formatted = Number(value).toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return `${formatted} MW`
}

export function formatSignedMW(value, decimals = 0) {
  if (value === null || value === undefined || isNaN(value)) {
    return '—'
  }
  const num = Number(value)
  const sign = num > 0 ? '+' : ''
  const formatted = num.toLocaleString('en-GB', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  })
  return `${sign}${formatted} MW`
}

export function formatDateTimeUTC(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString

    const day = String(d.getUTCDate()).padStart(2, '0')
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const month = months[d.getUTCMonth()]
    const year = d.getUTCFullYear()
    const hours = String(d.getUTCHours()).padStart(2, '0')
    const minutes = String(d.getUTCMinutes()).padStart(2, '0')

    return `${day} ${month} ${year}, ${hours}:${minutes} UTC`
  } catch {
    return isoString
  }
}

export function formatTimeOnlyUTC(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    const hours = String(d.getUTCHours()).padStart(2, '0')
    const minutes = String(d.getUTCMinutes()).padStart(2, '0')
    return `${hours}:${minutes}`
  } catch {
    return isoString
  }
}

export function formatShortDateUTC(isoString) {
  if (!isoString) return '—'
  try {
    const d = new Date(isoString)
    if (isNaN(d.getTime())) return isoString
    const day = String(d.getUTCDate()).padStart(2, '0')
    const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
    const month = months[d.getUTCMonth()]
    const hours = String(d.getUTCHours()).padStart(2, '0')
    const minutes = String(d.getUTCMinutes()).padStart(2, '0')
    return `${day} ${month} ${hours}:${minutes}`
  } catch {
    return isoString
  }
}

export function getStatusBadge(status) {
  switch (status) {
    case 'matched':
      return { label: 'Matched', className: 'badge-matched' }
    case 'missing_forecast':
      return { label: 'Missing Forecast', className: 'badge-missing-forecast' }
    case 'missing_actual':
      return { label: 'Missing Actual', className: 'badge-missing-actual' }
    default:
      return { label: status || 'Unknown', className: 'badge-neutral' }
  }
}
