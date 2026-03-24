import { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, ChevronsUpDown, Search } from 'lucide-react'
import type { QueryResult } from '../../api/types'

interface Props {
  result: QueryResult
}

type SortDir = 'asc' | 'desc' | null
const PAGE_SIZE = 20

function compareValues(a: unknown, b: unknown): number {
  if (a == null && b == null) return 0
  if (a == null) return -1
  if (b == null) return 1
  if (typeof a === 'number' && typeof b === 'number') return a - b
  return String(a).localeCompare(String(b), undefined, { numeric: true })
}

export function TableWidget({ result }: Props) {
  const [sortCol, setSortCol] = useState<string | null>(null)
  const [sortDir, setSortDir] = useState<SortDir>(null)
  const [filter, setFilter] = useState('')
  const [page, setPage] = useState(0)

  const filtered = useMemo(() => {
    if (!filter.trim()) return result.rows as Record<string, unknown>[]
    const q = filter.toLowerCase()
    return (result.rows as Record<string, unknown>[]).filter(row =>
      Object.values(row).some(v => v != null && String(v).toLowerCase().includes(q))
    )
  }, [result.rows, filter])

  const sorted = useMemo(() => {
    if (!sortCol || !sortDir) return filtered
    return [...filtered].sort((a, b) => {
      const cmp = compareValues(a[sortCol], b[sortCol])
      return sortDir === 'asc' ? cmp : -cmp
    })
  }, [filtered, sortCol, sortDir])

  const totalPages = Math.ceil(sorted.length / PAGE_SIZE)
  const pageRows = sorted.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE)

  const handleSort = (col: string) => {
    if (sortCol !== col) {
      setSortCol(col)
      setSortDir('asc')
      setPage(0)
    } else {
      const next: SortDir = sortDir === 'asc' ? 'desc' : sortDir === 'desc' ? null : 'asc'
      setSortDir(next)
      if (!next) setSortCol(null)
      setPage(0)
    }
  }

  const SortIcon = ({ col }: { col: string }) => {
    if (sortCol !== col) return <ChevronsUpDown size={11} className="text-gray-600" />
    if (sortDir === 'asc') return <ChevronUp size={11} className="text-brand-400" />
    return <ChevronDown size={11} className="text-brand-400" />
  }

  return (
    <div className="flex flex-col h-full gap-2">
      {/* Filter bar */}
      <div className="relative shrink-0">
        <Search size={12} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-gray-500" />
        <input
          type="text"
          value={filter}
          onChange={e => { setFilter(e.target.value); setPage(0) }}
          placeholder="Filtrer..."
          className="input-field text-xs pl-7 py-1.5"
        />
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        <table className="w-full text-xs border-collapse">
          <thead>
            <tr className="bg-gray-800 sticky top-0">
              {result.columns.map(col => (
                <th
                  key={col.name}
                  onClick={() => handleSort(col.name)}
                  className="px-3 py-2 text-left text-gray-400 font-medium border-b border-gray-700 cursor-pointer hover:text-gray-200 select-none whitespace-nowrap"
                >
                  <span className="flex items-center gap-1">
                    {col.name}
                    <SortIcon col={col.name} />
                  </span>
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {pageRows.map((row, i) => (
              <tr key={i} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-800/40'}>
                {result.columns.map(col => (
                  <td key={col.name} className="px-3 py-1.5 text-gray-300 border-b border-gray-800/50 max-w-xs truncate">
                    {(row as Record<string, unknown>)[col.name] == null
                      ? <span className="text-gray-600 italic">null</span>
                      : String((row as Record<string, unknown>)[col.name])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
        {pageRows.length === 0 && (
          <div className="flex items-center justify-center py-8 text-gray-600 text-xs">
            Aucune ligne{filter ? ' pour ce filtre' : ''}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between shrink-0 text-xs text-gray-500">
          <span>{sorted.length} ligne{sorted.length > 1 ? 's' : ''}{filter ? ` (filtré de ${result.total_count})` : ''}</span>
          <div className="flex items-center gap-2">
            <button onClick={() => setPage(p => Math.max(0, p - 1))} disabled={page === 0} className="btn-ghost py-0.5 px-2 disabled:opacity-40">‹</button>
            <span>{page + 1} / {totalPages}</span>
            <button onClick={() => setPage(p => Math.min(totalPages - 1, p + 1))} disabled={page >= totalPages - 1} className="btn-ghost py-0.5 px-2 disabled:opacity-40">›</button>
          </div>
        </div>
      )}
    </div>
  )
}
