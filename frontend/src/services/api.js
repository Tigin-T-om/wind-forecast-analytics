/**
 * API service for Wind Forecast Analytics backend.
 */

const API_BASE = '/api'

export async function fetchHealth() {
  const response = await fetch(`${API_BASE}/health`)
  if (!response.ok) {
    throw new Error(`Health check failed with status ${response.status}`)
  }
  return response.json()
}

export async function fetchAnalysis({
  startDate = '2026-01-01',
  endDate = '2026-01-31',
  cutoffPolicy = 'day_ahead_1700',
  resolution = 'hourly',
}) {
  const params = new URLSearchParams({
    start_date: startDate,
    end_date: endDate,
    cutoff_policy: cutoffPolicy,
    resolution: resolution,
  })

  const response = await fetch(`${API_BASE}/analysis?${params.toString()}`, {
    headers: {
      Accept: 'application/json',
    },
  })

  if (!response.ok) {
    let errorMessage = `API request failed with status ${response.status}`
    try {
      const errorData = await response.json()
      if (errorData.detail) {
        errorMessage = typeof errorData.detail === 'string' ? errorData.detail : JSON.stringify(errorData.detail)
      } else if (errorData.message) {
        errorMessage = errorData.message
      }
    } catch {
      // Fallback to default status message
    }
    throw new Error(errorMessage)
  }

  return response.json()
}
