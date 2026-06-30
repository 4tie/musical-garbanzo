'use client';

import { ReactNode, useMemo, useState } from 'react';
import { useThemeSettings } from './ThemeProvider';

type SortDirection = 'asc' | 'desc';

export interface DataTableColumn<T> {
  id: string;
  header: string;
  render: (row: T) => ReactNode;
  sortValue?: (row: T) => string | number | null | undefined;
  className?: string;
}

interface DataTableProps<T> {
  rows: T[];
  columns: DataTableColumn<T>[];
  getRowKey: (row: T) => string;
  onRowClick?: (row: T) => void;
  emptyState: ReactNode;
  initialSortColumn?: string;
  initialSortDirection?: SortDirection;
}

export default function DataTable<T>({
  rows,
  columns,
  getRowKey,
  onRowClick,
  emptyState,
  initialSortColumn,
  initialSortDirection = 'desc',
}: DataTableProps<T>) {
  const { density } = useThemeSettings();
  const [sortColumn, setSortColumn] = useState<string | null>(initialSortColumn ?? null);
  const [sortDirection, setSortDirection] = useState<SortDirection>(initialSortDirection);

  const sortedRows = useMemo(() => {
    if (!sortColumn) {
      return rows;
    }

    const column = columns.find((item) => item.id === sortColumn);
    if (!column?.sortValue) {
      return rows;
    }

    return [...rows].sort((left, right) => {
      const leftValue = column.sortValue?.(left);
      const rightValue = column.sortValue?.(right);
      const result = compareValues(leftValue, rightValue);
      return sortDirection === 'asc' ? result : -result;
    });
  }, [columns, rows, sortColumn, sortDirection]);

  if (rows.length === 0) {
    return <>{emptyState}</>;
  }

  const cellPadding = density === 'compact' ? 'px-3 py-2' : 'px-4 py-3';

  function handleSort(column: DataTableColumn<T>) {
    if (!column.sortValue) {
      return;
    }

    if (sortColumn === column.id) {
      setSortDirection((current) => (current === 'asc' ? 'desc' : 'asc'));
    } else {
      setSortColumn(column.id);
      setSortDirection('asc');
    }
  }

  return (
    <div className="overflow-hidden rounded-[var(--app-radius)] border border-[var(--app-border)]">
      <div className="overflow-auto">
        <table className="min-w-full border-collapse text-left text-sm">
          <thead className="sticky top-0 z-10 bg-[var(--app-surface-muted)] text-xs uppercase text-[var(--app-text-subtle)]">
            <tr>
              {columns.map((column) => {
                const sortable = Boolean(column.sortValue);
                const active = sortColumn === column.id;
                return (
                  <th key={column.id} className={[cellPadding, column.className ?? ''].join(' ')}>
                    <button
                      type="button"
                      disabled={!sortable}
                      onClick={() => handleSort(column)}
                      className={[
                        'flex items-center gap-1 font-semibold uppercase tracking-normal',
                        sortable
                          ? 'cursor-pointer text-[var(--app-text-muted)] hover:text-[var(--app-text)]'
                          : 'cursor-default text-[var(--app-text-subtle)]',
                      ].join(' ')}
                    >
                      {column.header}
                      {active && <span aria-hidden="true">{sortDirection === 'asc' ? '^' : 'v'}</span>}
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((row) => (
              <tr
                key={getRowKey(row)}
                tabIndex={onRowClick ? 0 : undefined}
                onClick={() => onRowClick?.(row)}
                onKeyDown={(event) => {
                  if (onRowClick && (event.key === 'Enter' || event.key === ' ')) {
                    event.preventDefault();
                    onRowClick(row);
                  }
                }}
                className={[
                  'border-t border-[var(--app-border)] bg-[var(--app-surface)] transition-colors',
                  onRowClick
                    ? 'cursor-pointer hover:bg-[var(--app-surface-muted)] focus:bg-[var(--app-surface-muted)] focus:outline-none'
                    : '',
                ].join(' ')}
              >
                {columns.map((column) => (
                  <td
                    key={`${getRowKey(row)}-${column.id}`}
                    className={[cellPadding, 'align-top text-[var(--app-text-muted)]', column.className ?? ''].join(' ')}
                  >
                    {column.render(row)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function compareValues(
  left: string | number | null | undefined,
  right: string | number | null | undefined,
): number {
  if (left == null && right == null) {
    return 0;
  }
  if (left == null) {
    return -1;
  }
  if (right == null) {
    return 1;
  }
  if (typeof left === 'number' && typeof right === 'number') {
    return left - right;
  }
  return String(left).localeCompare(String(right));
}
