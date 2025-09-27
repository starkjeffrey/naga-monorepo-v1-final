/**
 * DataGrid Pagination Component
 * Handles pagination controls and page size selection
 */

import React from 'react';
import { ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from 'lucide-react';
import { DataGridPagination as PaginationType } from '../types';

interface DataGridPaginationProps {
  pagination: PaginationType;
  onPaginationChange: (pagination: Partial<PaginationType>) => void;
  showPageSizeSelector?: boolean;
  showInfo?: boolean;
  compact?: boolean;
  className?: string;
}

export function DataGridPagination({
  pagination,
  onPaginationChange,
  showPageSizeSelector = true,
  showInfo = true,
  compact = false,
  className = ''
}: DataGridPaginationProps) {
  const { page, pageSize, total, pageSizeOptions = [10, 25, 50, 100, 200] } = pagination;

  const totalPages = Math.ceil(total / pageSize);
  const startItem = (page - 1) * pageSize + 1;
  const endItem = Math.min(page * pageSize, total);

  const canGoToPrevious = page > 1;
  const canGoToNext = page < totalPages;

  const handlePageChange = (newPage: number) => {
    if (newPage >= 1 && newPage <= totalPages) {
      onPaginationChange({ page: newPage });
    }
  };

  const handlePageSizeChange = (newPageSize: number) => {
    // Calculate new page to maintain approximate position
    const currentFirstItem = (page - 1) * pageSize;
    const newPage = Math.max(1, Math.ceil((currentFirstItem + 1) / newPageSize));

    onPaginationChange({
      pageSize: newPageSize,
      page: newPage
    });
  };

  const getPageNumbers = () => {
    const delta = compact ? 1 : 2;
    const range = [];
    const rangeWithDots = [];

    for (
      let i = Math.max(2, page - delta);
      i <= Math.min(totalPages - 1, page + delta);
      i++
    ) {
      range.push(i);
    }

    if (page - delta > 2) {
      rangeWithDots.push(1, '...');
    } else {
      rangeWithDots.push(1);
    }

    rangeWithDots.push(...range);

    if (page + delta < totalPages - 1) {
      rangeWithDots.push('...', totalPages);
    } else if (totalPages > 1) {
      rangeWithDots.push(totalPages);
    }

    return rangeWithDots;
  };

  const pageNumbers = getPageNumbers();

  // Don't render if no data
  if (total === 0) {
    return null;
  }

  const buttonBaseClass = `
    inline-flex items-center justify-center
    ${compact ? 'w-8 h-8 text-sm' : 'w-10 h-10'}
    border border-gray-300 bg-white text-gray-500
    hover:bg-gray-50 hover:text-gray-700
    disabled:opacity-50 disabled:cursor-not-allowed
    transition-colors duration-150
  `;

  const pageButtonClass = `
    ${buttonBaseClass}
    ${compact ? 'mx-0.5' : 'mx-1'}
  `;

  const activePageClass = `
    ${pageButtonClass}
    bg-blue-600 border-blue-600 text-white
    hover:bg-blue-700 hover:border-blue-700
  `;

  return (
    <div className={`bg-white border-t border-gray-200 px-6 py-3 ${className}`}>
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
        {/* Info */}
        {showInfo && (
          <div className="text-sm text-gray-700">
            Showing <span className="font-medium">{startItem}</span> to{' '}
            <span className="font-medium">{endItem}</span> of{' '}
            <span className="font-medium">{total}</span> results
          </div>
        )}

        {/* Pagination controls */}
        <div className="flex items-center justify-between sm:justify-end space-x-4">
          {/* Page size selector */}
          {showPageSizeSelector && (
            <div className="flex items-center space-x-2">
              <label className="text-sm text-gray-700">
                {compact ? 'Per page:' : 'Items per page:'}
              </label>
              <select
                value={pageSize}
                onChange={(e) => handlePageSizeChange(Number(e.target.value))}
                className="border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
              >
                {pageSizeOptions.map(size => (
                  <option key={size} value={size}>
                    {size}
                  </option>
                ))}
              </select>
            </div>
          )}

          {/* Page navigation */}
          <div className="flex items-center">
            {/* First page */}
            <button
              onClick={() => handlePageChange(1)}
              disabled={!canGoToPrevious}
              className={`${buttonBaseClass} rounded-l-md`}
              title="First page"
            >
              <ChevronsLeft className="w-4 h-4" />
            </button>

            {/* Previous page */}
            <button
              onClick={() => handlePageChange(page - 1)}
              disabled={!canGoToPrevious}
              className={`${buttonBaseClass} -ml-px`}
              title="Previous page"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>

            {/* Page numbers */}
            {!compact && pageNumbers.map((pageNum, index) => (
              <React.Fragment key={index}>
                {pageNum === '...' ? (
                  <span className="inline-flex items-center justify-center w-10 h-10 text-gray-500 -ml-px">
                    ...
                  </span>
                ) : (
                  <button
                    onClick={() => handlePageChange(pageNum as number)}
                    className={`
                      ${pageNum === page ? activePageClass : pageButtonClass}
                      -ml-px
                    `}
                  >
                    {pageNum}
                  </button>
                )}
              </React.Fragment>
            ))}

            {/* Current page indicator for compact mode */}
            {compact && (
              <div className="inline-flex items-center justify-center w-16 h-8 bg-gray-100 border-t border-b border-gray-300 text-sm text-gray-700 -ml-px">
                {page} / {totalPages}
              </div>
            )}

            {/* Next page */}
            <button
              onClick={() => handlePageChange(page + 1)}
              disabled={!canGoToNext}
              className={`${buttonBaseClass} -ml-px`}
              title="Next page"
            >
              <ChevronRight className="w-4 h-4" />
            </button>

            {/* Last page */}
            <button
              onClick={() => handlePageChange(totalPages)}
              disabled={!canGoToNext}
              className={`${buttonBaseClass} rounded-r-md -ml-px`}
              title="Last page"
            >
              <ChevronsRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Mobile-only page info */}
      {compact && (
        <div className="mt-2 text-xs text-gray-500 text-center sm:hidden">
          Page {page} of {totalPages} • {total} total items
        </div>
      )}
    </div>
  );
}

// Simple pagination component for basic use cases
export function SimplePagination({
  pagination,
  onPaginationChange,
  className = ''
}: Pick<DataGridPaginationProps, 'pagination' | 'onPaginationChange' | 'className'>) {
  return (
    <DataGridPagination
      pagination={pagination}
      onPaginationChange={onPaginationChange}
      showPageSizeSelector={false}
      compact={true}
      className={className}
    />
  );
}

// Page size selector component for separate use
interface PageSizeSelectorProps {
  pageSize: number;
  pageSizeOptions?: number[];
  onPageSizeChange: (pageSize: number) => void;
  label?: string;
  className?: string;
}

export function PageSizeSelector({
  pageSize,
  pageSizeOptions = [10, 25, 50, 100, 200],
  onPageSizeChange,
  label = 'Items per page:',
  className = ''
}: PageSizeSelectorProps) {
  return (
    <div className={`flex items-center space-x-2 ${className}`}>
      <label className="text-sm text-gray-700">{label}</label>
      <select
        value={pageSize}
        onChange={(e) => onPageSizeChange(Number(e.target.value))}
        className="border border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
      >
        {pageSizeOptions.map(size => (
          <option key={size} value={size}>
            {size}
          </option>
        ))}
      </select>
    </div>
  );
}

// Navigation-only pagination for minimal UI
interface NavigationPaginationProps {
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  showLabels?: boolean;
  className?: string;
}

export function NavigationPagination({
  page,
  totalPages,
  onPageChange,
  showLabels = true,
  className = ''
}: NavigationPaginationProps) {
  const canGoToPrevious = page > 1;
  const canGoToNext = page < totalPages;

  return (
    <div className={`flex items-center justify-between ${className}`}>
      <button
        onClick={() => onPageChange(page - 1)}
        disabled={!canGoToPrevious}
        className="flex items-center px-3 py-2 text-sm text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        <ChevronLeft className="w-4 h-4 mr-1" />
        {showLabels && 'Previous'}
      </button>

      <span className="text-sm text-gray-700">
        Page {page} of {totalPages}
      </span>

      <button
        onClick={() => onPageChange(page + 1)}
        disabled={!canGoToNext}
        className="flex items-center px-3 py-2 text-sm text-gray-500 bg-white border border-gray-300 rounded-md hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        {showLabels && 'Next'}
        <ChevronRight className="w-4 h-4 ml-1" />
      </button>
    </div>
  );
}