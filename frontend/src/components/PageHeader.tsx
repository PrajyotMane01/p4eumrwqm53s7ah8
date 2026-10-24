import type { Filters as FilterValues } from '../lib/filters'
import { Filters } from './Filters'

type Props = {
  title: string
  subtitle: string
  showFilters?: boolean
  filters: FilterValues
  defaultCutoff: string
  min: string
  max: string
  isDefault: boolean
  onChange: (next: Partial<FilterValues>) => void
  onReset: () => void
}

export function PageHeader({
  title,
  subtitle,
  showFilters = true,
  filters,
  defaultCutoff,
  min,
  max,
  isDefault,
  onChange,
  onReset,
}: Props) {
  return (
    <header className="page-header">
      <div>
        <h1>{title}</h1>
        <p className="subtitle">{subtitle}</p>
      </div>
      {showFilters && (
        <Filters
          {...filters}
          defaultCutoff={defaultCutoff}
          min={min}
          max={max}
          isDefault={isDefault}
          onChange={onChange}
          onReset={onReset}
        />
      )}
    </header>
  )
}
