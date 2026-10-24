import { useState, useMemo } from 'react'
import {
  formatMW,
  formatSignedMW,
  formatDateTimeUTC,
  getStatusBadge,
} from '../utils/formatters'

export default function GenerationTable({ observations = [] }) {
  const [currentPage, setCurrentPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [statusFilter, setStatusFilter] = useState('all') // 'all', 'matched', 'missing_forecast', 'missing_actual'
  const [sortField, setSortField] = useState('delivery_timestamp')
  const [sortAsc, setSortAsc] = useState(true)

  // Filter observations
  const filteredData = useMemo(() => {
    return observations.filter((item) => {
      if (statusFilter === 'all') return true
      return item.status === statusFilter
    })
  }, [observations, statusFilter])

  // Sort observations
  const sortedData = useMemo(() => {
    const list = [...filteredData]
    list.sort((a, b) => {
      let valA = a[sortField]
      let valB = b[sortField]

      if (valA === null || valA === undefined) return 1
      if (valB === null || valB === undefined) return -1

      if (typeof valA === 'string') {
        const cmp = valA.localeCompare(valB)
        return sortAsc ? cmp : -cmp
      }
      return sortAsc ? valA - valB : valB - valA
    })
    return list
  }, [filteredData, sortField, sortAsc])

  // Pagination
  const totalRows = sortedData.length
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize))
  const startIndex = (currentPage - 1) * pageSize
  const paginatedData = sortedData.slice(startIndex, startIndex + pageSize)

  const handleSort = (field) => {
    if (sortField === field) {
      setSortAsc(!sortAsc)
    } else {
      setSortField(field)
      setSortAsc(true)
    }
  }

  const exportCSV = () => {
    if (observations.length === 0) return

    const headers = [
      'Delivery Start (UTC)',
      'Delivery End (UTC)',
      'Forecast Publication Time (UTC)',
      'Forecast Generation (MW)',
      'Actual Generation (MW)',
      'Signed Error (MW)',
      'Absolute Error (MW)',
      'Status',
    ]

    const rows = sortedData.map((d) => [
      d.delivery_timestamp || '',
      d.delivery_end_timestamp || '',
      d.forecast_publish_time || '',
      d.forecast_mw !== null ? d.forecast_mw : '',
      d.actual_mw !== null ? d.actual_mw : '',
      d.signed_error !== null ? d.signed_error : '',
      d.absolute_error !== null ? d.absolute_error : '',
      d.status || '',
    ])

    const csvContent = [
      headers.join(','),
      ...rows.map((row) => row.map((val) => `"${String(val).replace(/"/g, '""')}"`).join(',')),
    ].join('\n')

    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', `wind_forecast_analysis_${new Date().toISOString().slice(0, 10)}.csv`)
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
  }

  return (
    <div className="table-card">
      <div className="table-header-row">
        <div>
          <h2 className="table-title">Delivery Interval Observations</h2>
          <p className="table-subtitle">
            Chronological comparison of metered actuals and day-ahead wind forecasts
          </p>
        </div>

        <div className="table-actions">
          <div className="filter-select-wrapper">
            <label htmlFor="table-status-filter" className="sr-only">
              Filter by Status
            </label>
            <select
              id="table-status-filter"
              className="table-filter-select"
              value={statusFilter}
              onChange={(e) => {
                setStatusFilter(e.target.value)
                setCurrentPage(1)
              }}
            >
              <option value="all">All Statuses ({observations.length})</option>
              <option value="matched">Matched Only</option>
              <option value="missing_forecast">Missing Forecast</option>
              <option value="missing_actual">Missing Actual</option>
            </select>
          </div>

          <button
            type="button"
            className="btn btn-secondary btn-export"
            onClick={exportCSV}
            title="Download table data as CSV"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            Export CSV
          </button>
        </div>
      </div>

      <div className="table-responsive">
        <table className="data-table">
          <thead>
            <tr>
              <th onClick={() => handleSort('delivery_timestamp')} className="sortable-th">
                Delivery Timestamp (UTC)
                {sortField === 'delivery_timestamp' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('forecast_publish_time')} className="sortable-th">
                Forecast Published (UTC)
                {sortField === 'forecast_publish_time' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('forecast_mw')} className="sortable-th text-right">
                Forecast (MW)
                {sortField === 'forecast_mw' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('actual_mw')} className="sortable-th text-right">
                Actual (MW)
                {sortField === 'actual_mw' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('signed_error')} className="sortable-th text-right">
                Signed Error (MW)
                {sortField === 'signed_error' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th onClick={() => handleSort('absolute_error')} className="sortable-th text-right">
                Abs Error (MW)
                {sortField === 'absolute_error' && (
                  <span className="sort-icon">{sortAsc ? ' ↑' : ' ↓'}</span>
                )}
              </th>
              <th className="text-center">Status</th>
            </tr>
          </thead>
          <tbody>
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan="7" className="table-empty-message">
                  No observations match the selected criteria.
                </td>
              </tr>
            ) : (
              paginatedData.map((row) => {
                const badge = getStatusBadge(row.status)
                return (
                  <tr key={row.delivery_timestamp}>
                    <td className="font-mono text-primary">
                      {formatDateTimeUTC(row.delivery_timestamp)}
                    </td>
                    <td className="font-mono text-muted">
                      {formatDateTimeUTC(row.forecast_publish_time)}
                    </td>
                    <td className="font-mono text-right">
                      {formatMW(row.forecast_mw)}
                    </td>
                    <td className="font-mono text-right text-bold">
                      {formatMW(row.actual_mw)}
                    </td>
                    <td className="font-mono text-right">
                      {row.signed_error !== null ? (
                        <span
                          className={
                            row.signed_error > 0
                              ? 'error-positive font-bold'
                              : row.signed_error < 0
                              ? 'error-negative font-bold'
                              : ''
                          }
                        >
                          {formatSignedMW(row.signed_error)}
                        </span>
                      ) : (
                        '—'
                      )}
                    </td>
                    <td className="font-mono text-right">
                      {row.absolute_error !== null
                        ? formatMW(row.absolute_error)
                        : '—'}
                    </td>
                    <td className="text-center">
                      <span className={`status-badge ${badge.className}`}>
                        {badge.label}
                      </span>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination controls */}
      <div className="table-pagination-row">
        <div className="pagination-info">
          Showing {totalRows > 0 ? startIndex + 1 : 0} to{' '}
          {Math.min(startIndex + pageSize, totalRows)} of {totalRows.toLocaleString('en-GB')} intervals
        </div>

        <div className="pagination-controls">
          <label htmlFor="page-size-select" className="sr-only">
            Rows per page
          </label>
          <select
            id="page-size-select"
            className="page-size-select"
            value={pageSize}
            onChange={(e) => {
              setPageSize(Number(e.target.value))
              setCurrentPage(1)
            }}
          >
            <option value="25">25 rows</option>
            <option value="50">50 rows</option>
            <option value="100">100 rows</option>
          </select>

          <button
            type="button"
            className="btn btn-pagination"
            onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
            disabled={currentPage <= 1}
          >
            Previous
          </button>
          <span className="pagination-current">
            Page {currentPage} of {totalPages}
          </span>
          <button
            type="button"
            className="btn btn-pagination"
            onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
            disabled={currentPage >= totalPages}
          >
            Next
          </button>
        </div>
      </div>
    </div>
  )
}
