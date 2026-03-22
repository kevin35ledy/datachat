import type { QueryResult } from '../../api/types'
import { ResultTable } from '../chat/ResultTable'

interface Props {
  result: QueryResult
}

export function TableWidget({ result }: Props) {
  return (
    <div className="h-full overflow-auto">
      <ResultTable result={result} />
    </div>
  )
}
