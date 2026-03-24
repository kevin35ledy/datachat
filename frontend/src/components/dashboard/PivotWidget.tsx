import type { QueryResult, WidgetConfig, PivotAggregation } from '../../api/types'

interface Props {
  result: QueryResult
  config: WidgetConfig
}

type AggFn = (values: number[]) => number

const AGG_FNS: Record<string, AggFn> = {
  sum:   (v) => v.reduce((a, b) => a + b, 0),
  count: (v) => v.length,
  avg:   (v) => v.length ? v.reduce((a, b) => a + b, 0) / v.length : 0,
  min:   (v) => Math.min(...v),
  max:   (v) => Math.max(...v),
}

const AGG_SHORT: Record<string, string> = {
  sum: 'Somme', count: 'Nb.', avg: 'Moy.', min: 'Min.', max: 'Max.',
}

function aggLabel(a: PivotAggregation): string {
  return a.label || `${AGG_SHORT[a.agg] ?? a.agg} de ${a.field}`
}

function fmt(v: number): string {
  return Number.isInteger(v)
    ? v.toLocaleString('fr-FR')
    : v.toLocaleString('fr-FR', { maximumFractionDigits: 2 })
}

function cellLabel(val: unknown): string {
  if (val === null || val === undefined || String(val).trim() === '') return '(vide)'
  return String(val)
}

function uniqueCombos(rows: Record<string, unknown>[], cols: string[]): string[][] {
  const seen = new Set<string>()
  const out: string[][] = []
  for (const row of rows) {
    const combo = cols.map(c => cellLabel(row[c]))
    const k = combo.join('\0')
    if (!seen.has(k)) { seen.add(k); out.push(combo) }
  }
  return out
}

// Build thead rows for column dimension headers (with colSpan grouping)
// + optional last row for agg labels when multiple aggs
function buildColHeaders(
  colCombos: string[][],
  colDims: string[],
  aggs: PivotAggregation[],
): { label: string; span: number }[][] {
  const rows: { label: string; span: number }[][] = []
  for (let level = 0; level < colDims.length; level++) {
    const row: { label: string; span: number }[] = []
    let i = 0
    while (i < colCombos.length) {
      const prefix = colCombos[i].slice(0, level + 1).join('\0')
      let span = 1
      while (i + span < colCombos.length &&
        colCombos[i + span].slice(0, level + 1).join('\0') === prefix) span++
      row.push({ label: colCombos[i][level], span: span * aggs.length })
      i += span
    }
    rows.push(row)
  }
  if (aggs.length > 1) {
    rows.push(colCombos.flatMap(() => aggs.map(a => ({ label: aggLabel(a), span: 1 }))))
  }
  return rows
}

// ─── Styles ───────────────────────────────────────────────────────────────────
const S = {
  table: 'text-xs w-full border-collapse',
  // Header
  th: 'border border-gray-600 px-2.5 py-1.5 font-semibold whitespace-nowrap bg-gray-800 text-gray-200',
  thDim: 'border border-gray-600 px-2.5 py-1.5 font-semibold bg-gray-700 text-gray-300 text-left',
  thTotal: 'border border-gray-600 px-2.5 py-1.5 font-semibold bg-gray-700 text-brand-400 text-right whitespace-nowrap',
  // Data cells
  tdDim: 'border border-gray-700 px-2.5 py-1 text-gray-200 font-medium whitespace-nowrap text-left',
  tdVal: 'border border-gray-700 px-2.5 py-1 tabular-nums text-right text-gray-100',
  tdRowTotal: 'border border-gray-700 px-2.5 py-1 tabular-nums text-right font-semibold text-brand-400',
  // Footer (totals row)
  tfoot: 'bg-gray-700',
  tfTd: 'border border-gray-600 px-2.5 py-1.5 tabular-nums text-right font-semibold text-brand-400',
  tfGrand: 'border border-gray-600 px-2.5 py-1.5 tabular-nums text-right font-bold text-brand-300',
  tfLabel: 'border border-gray-600 px-2.5 py-1.5 font-semibold text-brand-400 text-left',
}

export function PivotWidget({ result, config }: Props) {
  const {
    pivot_row_cols = [],
    pivot_col_cols = [],
    pivot_aggregations = [],
  } = config

  const aggs = pivot_aggregations
  const rows = result.rows as Record<string, unknown>[]

  if (!aggs.length || (!pivot_row_cols.length && !pivot_col_cols.length)) {
    return (
      <div className="flex items-center justify-center h-full text-gray-500 text-sm text-center px-4">
        Configurez les dimensions du TCD (⚙ lignes / colonnes / agrégations)
      </div>
    )
  }

  const mode = pivot_row_cols.length && pivot_col_cols.length ? 'full'
    : pivot_row_cols.length ? 'rows-only'
    : 'cols-only'

  // ─── Lookup: lookup[rowKey][colKey][aggIdx] = number[] ───────────────────
  const lookup: Record<string, Record<string, Record<number, number[]>>> = {}
  for (const row of rows) {
    const rk = pivot_row_cols.length
      ? pivot_row_cols.map(c => cellLabel(row[c])).join('\0') : ''
    const ck = pivot_col_cols.length
      ? pivot_col_cols.map(c => cellLabel(row[c])).join('\0') : ''
    for (let ai = 0; ai < aggs.length; ai++) {
      const raw = row[aggs[ai].field]
      const num = typeof raw === 'number' ? raw : Number(raw)
      if (!isNaN(num)) {
        ;(lookup[rk] ??= {})
        ;(lookup[rk][ck] ??= {})
        ;(lookup[rk][ck][ai] ??= []).push(num)
      }
    }
  }

  const aggFn = (a: PivotAggregation) => AGG_FNS[a.agg] ?? AGG_FNS.sum

  const cell = (rk: string, ck: string, ai: number): number => {
    const vals = lookup[rk]?.[ck]?.[ai]
    return vals?.length ? aggFn(aggs[ai])(vals) : 0
  }

  // ─── MODE rows-only ───────────────────────────────────────────────────────
  if (mode === 'rows-only') {
    const rowCombos = uniqueCombos(rows, pivot_row_cols)
    const multiAgg = aggs.length > 1

    const rowSum = (rk: string): number => {
      const all = aggs.flatMap((_, ai) => lookup[rk]?.['']?.[ai] ?? [])
      // sum of all individual agg results per row (just for a grand row total)
      return aggs.reduce((acc, a, ai) => {
        const vals = lookup[rk]?.['']?.[ai]
        return acc + (vals?.length ? aggFn(a)(vals) : 0)
      }, 0)
    }

    return (
      <div className="h-full overflow-auto">
        <table className={S.table}>
          <thead>
            <tr>
              {pivot_row_cols.map(rc => (
                <th key={rc} className={S.thDim}>{rc}</th>
              ))}
              {aggs.map((a, ai) => (
                <th key={ai} className={S.th + ' text-right'}>{aggLabel(a)}</th>
              ))}
              {multiAgg && <th className={S.thTotal}>Total</th>}
            </tr>
          </thead>
          <tbody>
            {rowCombos.map((rc, i) => {
              const rk = rc.join('\0')
              return (
                <tr key={rk} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-850'}>
                  {rc.map((val, j) => <td key={j} className={S.tdDim}>{val}</td>)}
                  {aggs.map((_, ai) => (
                    <td key={ai} className={S.tdVal}>{fmt(cell(rk, '', ai))}</td>
                  ))}
                  {multiAgg && <td className={S.tdRowTotal}>{fmt(rowSum(rk))}</td>}
                </tr>
              )
            })}
          </tbody>
          <tfoot className={S.tfoot}>
            <tr>
              <td colSpan={pivot_row_cols.length} className={S.tfLabel}>Total</td>
              {aggs.map((a, ai) => {
                const all = rowCombos.flatMap(rc => lookup[rc.join('\0')]?.['']?.[ai] ?? [])
                return <td key={ai} className={S.tfTd}>{fmt(all.length ? aggFn(a)(all) : 0)}</td>
              })}
              {multiAgg && (() => {
                const grand = aggs.reduce((acc, a, ai) => {
                  const all = rowCombos.flatMap(rc => lookup[rc.join('\0')]?.['']?.[ai] ?? [])
                  return acc + (all.length ? aggFn(a)(all) : 0)
                }, 0)
                return <td className={S.tfGrand}>{fmt(grand)}</td>
              })()}
            </tr>
          </tfoot>
        </table>
      </div>
    )
  }

  // ─── MODE cols-only ───────────────────────────────────────────────────────
  if (mode === 'cols-only') {
    const colCombos = uniqueCombos(rows, pivot_col_cols)
    const colHeaders = buildColHeaders(colCombos, pivot_col_cols, aggs)
    const nHeaderRows = Math.max(colHeaders.length, 1)
    const multiAgg = aggs.length > 1

    return (
      <div className="h-full overflow-auto">
        <table className={S.table}>
          <thead>
            {colHeaders.map((headerRow, level) => (
              <tr key={level}>
                {level === 0 && multiAgg && (
                  <th rowSpan={nHeaderRows} className={S.thDim + ' min-w-[90px]'} />
                )}
                {headerRow.map((cell, i) => (
                  <th key={i} colSpan={cell.span} className={S.th + ' text-right'}>{cell.label}</th>
                ))}
                {level === 0 && <th rowSpan={nHeaderRows} className={S.thTotal}>Total</th>}
              </tr>
            ))}
            {colHeaders.length === 0 && (
              <tr>
                {colCombos.map((cc, i) => (
                  <th key={i} className={S.th + ' text-right'}>{cc.join(' · ')}</th>
                ))}
                <th className={S.thTotal}>Total</th>
              </tr>
            )}
          </thead>
          <tbody>
            {multiAgg ? (
              aggs.map((a, ai) => (
                <tr key={ai} className={ai % 2 === 0 ? 'bg-gray-900' : 'bg-gray-850'}>
                  <td className={S.tdDim}>{aggLabel(a)}</td>
                  {colCombos.map((cc, ci) => (
                    <td key={ci} className={S.tdVal}>{fmt(cell('', cc.join('\0'), ai))}</td>
                  ))}
                  <td className={S.tdRowTotal}>
                    {fmt((() => {
                      const all = colCombos.flatMap(cc => lookup['']?.[cc.join('\0')]?.[ai] ?? [])
                      return all.length ? aggFn(a)(all) : 0
                    })())}
                  </td>
                </tr>
              ))
            ) : (
              <tr className="bg-gray-900">
                {colCombos.map((cc, ci) => (
                  <td key={ci} className={S.tdVal}>{fmt(cell('', cc.join('\0'), 0))}</td>
                ))}
                <td className={S.tdRowTotal}>
                  {fmt((() => {
                    const all = colCombos.flatMap(cc => lookup['']?.[cc.join('\0')]?.[0] ?? [])
                    return all.length ? aggFn(aggs[0])(all) : 0
                  })())}
                </td>
              </tr>
            )}
          </tbody>
          <tfoot className={S.tfoot}>
            <tr>
              {multiAgg && <td className={S.tfLabel}>Total</td>}
              {colCombos.map((cc, ci) => {
                const all = aggs.flatMap((a, ai) => {
                  const vals = lookup['']?.[cc.join('\0')]?.[ai] ?? []
                  return vals.length ? [aggFn(a)(vals)] : []
                })
                return <td key={ci} className={S.tfTd}>{fmt(all.reduce((a, b) => a + b, 0))}</td>
              })}
              <td className={S.tfGrand}>
                {fmt(aggs.reduce((acc, a, ai) => {
                  const all = colCombos.flatMap(cc => lookup['']?.[cc.join('\0')]?.[ai] ?? [])
                  return acc + (all.length ? aggFn(a)(all) : 0)
                }, 0))}
              </td>
            </tr>
          </tfoot>
        </table>
      </div>
    )
  }

  // ─── MODE full (lignes + colonnes + agrégations) ──────────────────────────
  const rowCombos = uniqueCombos(rows, pivot_row_cols)
  const colCombos = uniqueCombos(rows, pivot_col_cols)
  const colHeaders = buildColHeaders(colCombos, pivot_col_cols, aggs)
  const nHeaderRows = colHeaders.length

  const rowTotal = (rk: string): number =>
    aggs.reduce((acc, a, ai) => {
      const all = colCombos.flatMap(cc => lookup[rk]?.[cc.join('\0')]?.[ai] ?? [])
      return acc + (all.length ? aggFn(a)(all) : 0)
    }, 0)

  const colAggTotal = (ck: string, ai: number): number => {
    const all = rowCombos.flatMap(rc => lookup[rc.join('\0')]?.[ck]?.[ai] ?? [])
    return all.length ? aggFn(aggs[ai])(all) : 0
  }

  const grandTotal = (): number =>
    aggs.reduce((acc, a, ai) => {
      const all = rowCombos.flatMap(rc =>
        colCombos.flatMap(cc => lookup[rc.join('\0')]?.[cc.join('\0')]?.[ai] ?? [])
      )
      return acc + (all.length ? aggFn(a)(all) : 0)
    }, 0)

  return (
    <div className="h-full overflow-auto">
      <table className={S.table}>
        <thead>
          {colHeaders.map((headerRow, level) => (
            <tr key={level}>
              {level === 0 && (
                <th
                  colSpan={pivot_row_cols.length}
                  rowSpan={nHeaderRows}
                  className={S.thDim}
                >
                  {pivot_row_cols.join(' / ')} \ {pivot_col_cols.join(' / ')}
                </th>
              )}
              {headerRow.map((cell, i) => (
                <th key={i} colSpan={cell.span} className={S.th + ' text-right'}>{cell.label}</th>
              ))}
              {level === 0 && (
                <th rowSpan={nHeaderRows} className={S.thTotal}>Total</th>
              )}
            </tr>
          ))}
        </thead>
        <tbody>
          {rowCombos.map((rc, i) => {
            const rk = rc.join('\0')
            return (
              <tr key={rk} className={i % 2 === 0 ? 'bg-gray-900' : 'bg-gray-850'}>
                {rc.map((val, j) => <td key={j} className={S.tdDim}>{val}</td>)}
                {colCombos.flatMap((cc, ci) =>
                  aggs.map((_, ai) => (
                    <td key={`${ci}-${ai}`} className={S.tdVal}>
                      {fmt(cell(rk, cc.join('\0'), ai))}
                    </td>
                  ))
                )}
                <td className={S.tdRowTotal}>{fmt(rowTotal(rk))}</td>
              </tr>
            )
          })}
        </tbody>
        <tfoot className={S.tfoot}>
          <tr>
            <td colSpan={pivot_row_cols.length} className={S.tfLabel}>Total</td>
            {colCombos.flatMap((cc, ci) =>
              aggs.map((_, ai) => (
                <td key={`${ci}-${ai}`} className={S.tfTd}>
                  {fmt(colAggTotal(cc.join('\0'), ai))}
                </td>
              ))
            )}
            <td className={S.tfGrand}>{fmt(grandTotal())}</td>
          </tr>
        </tfoot>
      </table>
    </div>
  )
}
