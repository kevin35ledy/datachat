import { useState } from 'react'
import type { QueryResult } from '../../api/types'
import { Download, AlertTriangle } from 'lucide-react'

interface ResultTableProps {
  result: QueryResult
}

const PAGE_SIZE = 20

export function ResultTable({ result }: ResultTableProps) {
  const [page, setPage] = useState(0)
  const totalPages = Math.ceil(result.rows.length / PAGE_SIZE)
  const visibleRows = result.rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleExportCSV = () => {
    const headers = result.columns.map((c) => c.name).join(',')
    const rows = result.rows
      .map((row) =>
        result.columns
          .map((c) => {
            const v = row[c.name]
            if (v === null || v === undefined) return ''
            const str = String(v)
            return str.includes(',') || str.includes('"') ? `"${str.replace(/"/g, '""')}"` : str
          })
          .join(',')
      )
      .join('\n')
    const blob = new Blob([headers + '\n' + rows], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'results.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="space-y-2">
      {/* Metadata bar */}
      <div className="flex items-center gap-3 text-xs text-gray-500">
        <span>{result.total_count.toLocaleString()} ligne(s)</span>
        {result.truncated && (
          <span className="flex items-center gap-1 text-yellow-500">
            <AlertTriangle size={10} />
            Résultats tronqués
          </span>
        )}
        <button onClick={handleExportCSV} className="flex items-center gap-1 ml-auto hover:text-gray-300 transition-colors">
          <Download size={12} />
          CSV
        </button>
      </div>

      {/* Table */}
      <div className="overflow-x-auto rounded-lg border border-gray-700">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-800">
              {result.columns.map((col) => (
                <th
                  key={col.name}
                  className="px-3 py-2 text-left text-gray-400 font-medium whitespace-nowrap"
                >
                  {col.name}
                  <span className="ml-1 text-gray-600 font-normal">{col.type_name}</span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row, i) => (
              <tr key={i} className="border-t border-gray-800 hover:bg-gray-800/50 transition-colors">
                {result.columns.map((col) => (
                  <td key={col.name} className="px-3 py-2 text-gray-300 whitespace-nowrap max-w-xs truncate">
                    {row[col.name] === null || row[col.name] === undefined ? (
                      <span className="text-gray-600 italic">null</span>
                    ) : (
                      String(row[col.name])
                    )}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center gap-2 justify-center text-xs">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="btn-ghost py-1 px-2 disabled:opacity-30"
          >
            ←
          </button>
          <span className="text-gray-500">
            {page + 1} / {totalPages}
          </span>
          <button
            onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
            disabled={page >= totalPages - 1}
            className="btn-ghost py-1 px-2 disabled:opacity-30"
          >
            →
          </button>
        </div>
      )}
    </div>
  )
}
