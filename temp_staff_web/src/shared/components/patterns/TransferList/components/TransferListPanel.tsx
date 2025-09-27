/**
 * TransferList Panel Component
 * Individual panel for left or right side of transfer list
 */

import React, { useState, useMemo } from 'react';
import { FixedSizeList as List } from 'react-window';
import {
  Search,
  Filter,
  MoreVertical,
  ChevronDown,
  X,
  Check,
  Users,
  Eye,
  EyeOff
} from 'lucide-react';
import {
  TransferItem,
  TransferListFilter,
  TransferCategory
} from '../types';

interface TransferListPanelProps {
  // Data
  items: TransferItem[];
  selectedItems: Set<string | number>;

  // Configuration
  side: 'left' | 'right';
  title: string;
  subtitle?: string;

  // Features
  searchable?: boolean;
  filterable?: boolean;
  categorizable?: boolean;
  virtualScrolling?: boolean;

  // Search
  searchQuery: string;
  searchPlaceholder?: string;
  onSearchChange: (query: string) => void;

  // Filters
  filters?: TransferListFilter[];
  activeFilters: Record<string, any>;
  onFilterChange: (filterId: string, value: any) => void;
  onClearFilters: () => void;

  // Categories
  categories?: TransferCategory[];
  selectedCategories: string[];
  onCategoryToggle: (categoryId: string) => void;

  // Selection
  onItemToggle: (itemId: string | number) => void;
  onSelectAll: () => void;
  onClearSelection: () => void;

  // Styling
  height?: number;
  itemHeight?: number;
  className?: string;

  // Customization
  renderItem?: (item: TransferItem, selected: boolean) => React.ReactNode;
  renderEmpty?: () => React.ReactNode;

  // Accessibility
  ariaLabel?: string;
}

export function TransferListPanel({
  items,
  selectedItems,
  side,
  title,
  subtitle,
  searchable = true,
  filterable = true,
  categorizable = false,
  virtualScrolling = false,
  searchQuery,
  searchPlaceholder,
  onSearchChange,
  filters = [],
  activeFilters,
  onFilterChange,
  onClearFilters,
  categories = [],
  selectedCategories,
  onCategoryToggle,
  onItemToggle,
  onSelectAll,
  onClearSelection,
  height = 400,
  itemHeight = 48,
  className = '',
  renderItem,
  renderEmpty,
  ariaLabel
}: TransferListPanelProps) {
  const [showFilters, setShowFilters] = useState(false);
  const [showCategories, setShowCategories] = useState(false);

  const hasActiveFilters = Object.values(activeFilters).some(value =>
    value !== undefined && value !== null && value !== ''
  );

  const allSelected = items.length > 0 && items.every(item => selectedItems.has(item.id));
  const someSelected = items.some(item => selectedItems.has(item.id));

  // Handle item selection
  const handleItemClick = (item: TransferItem, event: React.MouseEvent) => {
    if (item.disabled) return;

    // Allow Ctrl/Cmd click for multi-selection
    if (!event.ctrlKey && !event.metaKey) {
      onItemToggle(item.id);
    } else {
      onItemToggle(item.id);
    }
  };

  // Handle select all/none
  const handleSelectAllToggle = () => {
    if (allSelected) {
      onClearSelection();
    } else {
      onSelectAll();
    }
  };

  // Category filtering
  const categorizedItems = useMemo(() => {
    if (!categorizable || selectedCategories.length === 0) {
      return items;
    }
    return items.filter(item =>
      selectedCategories.includes(item.category || 'uncategorized')
    );
  }, [items, categorizable, selectedCategories]);

  // Virtual list item renderer
  const VirtualListItem = ({ index, style }: { index: number; style: React.CSSProperties }) => {
    const item = categorizedItems[index];
    const isSelected = selectedItems.has(item.id);

    return (
      <div style={style}>
        <TransferListItem
          item={item}
          selected={isSelected}
          onClick={(event) => handleItemClick(item, event)}
          renderContent={renderItem}
        />
      </div>
    );
  };

  return (
    <div className={`bg-white border border-gray-200 rounded-lg flex flex-col ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between mb-3">
          <div>
            <h3 className="text-lg font-medium text-gray-900">{title}</h3>
            {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
          </div>

          <div className="flex items-center space-x-2">
            {/* Item count */}
            <span className="text-sm text-gray-500">
              {selectedItems.size > 0 && `${selectedItems.size} / `}
              {items.length}
            </span>

            {/* Select all toggle */}
            {items.length > 0 && (
              <button
                onClick={handleSelectAllToggle}
                className="p-2 text-gray-400 hover:text-gray-600 rounded-md hover:bg-gray-100"
                title={allSelected ? 'Deselect all' : 'Select all'}
              >
                {allSelected ? <Eye className="w-4 h-4" /> : <EyeOff className="w-4 h-4" />}
              </button>
            )}

            {/* Filter toggle */}
            {filterable && filters.length > 0 && (
              <button
                onClick={() => setShowFilters(!showFilters)}
                className={`p-2 rounded-md hover:bg-gray-100 ${
                  hasActiveFilters ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
                }`}
                title="Toggle filters"
              >
                <Filter className="w-4 h-4" />
              </button>
            )}

            {/* Category toggle */}
            {categorizable && categories.length > 0 && (
              <button
                onClick={() => setShowCategories(!showCategories)}
                className={`p-2 rounded-md hover:bg-gray-100 ${
                  selectedCategories.length > 0 ? 'text-blue-600' : 'text-gray-400 hover:text-gray-600'
                }`}
                title="Toggle categories"
              >
                <Users className="w-4 h-4" />
              </button>
            )}
          </div>
        </div>

        {/* Search */}
        {searchable && (
          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
            <input
              type="text"
              placeholder={searchPlaceholder || `Search ${title.toLowerCase()}...`}
              value={searchQuery}
              onChange={(e) => onSearchChange(e.target.value)}
              className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
            />
          </div>
        )}

        {/* Filters */}
        {showFilters && filterable && (
          <div className="mt-3 space-y-2">
            {filters.map(filter => (
              <FilterControl
                key={filter.id}
                filter={filter}
                value={activeFilters[filter.id]}
                onChange={(value) => onFilterChange(filter.id, value)}
              />
            ))}
            {hasActiveFilters && (
              <button
                onClick={onClearFilters}
                className="text-sm text-blue-600 hover:text-blue-700 flex items-center"
              >
                <X className="w-3 h-3 mr-1" />
                Clear filters
              </button>
            )}
          </div>
        )}

        {/* Categories */}
        {showCategories && categorizable && (
          <div className="mt-3">
            <div className="flex flex-wrap gap-2">
              {categories.map(category => (
                <button
                  key={category.id}
                  onClick={() => onCategoryToggle(category.id)}
                  className={`px-3 py-1 text-sm rounded-full border ${
                    selectedCategories.includes(category.id)
                      ? 'bg-blue-100 text-blue-800 border-blue-300'
                      : 'bg-gray-100 text-gray-700 border-gray-300 hover:bg-gray-200'
                  }`}
                >
                  {category.icon && <span className="mr-1">{category.icon}</span>}
                  {category.label}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Items list */}
      <div className="flex-1 overflow-hidden" style={{ height: height - 120 }}>
        {categorizedItems.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            {renderEmpty ? renderEmpty() : (
              <div className="text-center">
                <div className="text-lg font-medium mb-2">No items</div>
                <div className="text-sm">
                  {hasActiveFilters || searchQuery
                    ? 'Try adjusting your search or filters'
                    : 'No items available'
                  }
                </div>
              </div>
            )}
          </div>
        ) : virtualScrolling && categorizedItems.length > 100 ? (
          <List
            height={height - 120}
            itemCount={categorizedItems.length}
            itemSize={itemHeight}
          >
            {VirtualListItem}
          </List>
        ) : (
          <div className="overflow-y-auto h-full">
            {categorizedItems.map(item => {
              const isSelected = selectedItems.has(item.id);
              return (
                <TransferListItem
                  key={item.id}
                  item={item}
                  selected={isSelected}
                  onClick={(event) => handleItemClick(item, event)}
                  renderContent={renderItem}
                />
              );
            })}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-gray-200 bg-gray-50">
        <div className="flex items-center justify-between text-sm text-gray-600">
          <span>
            {selectedItems.size > 0 ? (
              <>
                {selectedItems.size} selected
                {someSelected && !allSelected && ` of ${items.length}`}
              </>
            ) : (
              `${items.length} items`
            )}
          </span>

          {selectedItems.size > 0 && (
            <button
              onClick={onClearSelection}
              className="text-blue-600 hover:text-blue-700 text-sm"
            >
              Clear selection
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// Individual item component
interface TransferListItemProps {
  item: TransferItem;
  selected: boolean;
  onClick: (event: React.MouseEvent) => void;
  renderContent?: (item: TransferItem, selected: boolean) => React.ReactNode;
}

function TransferListItem({
  item,
  selected,
  onClick,
  renderContent
}: TransferListItemProps) {
  if (renderContent) {
    return (
      <div
        onClick={onClick}
        className={`cursor-pointer border-b border-gray-100 last:border-b-0 ${
          item.disabled ? 'opacity-50 cursor-not-allowed' : ''
        }`}
      >
        {renderContent(item, selected)}
      </div>
    );
  }

  return (
    <div
      onClick={onClick}
      className={`
        flex items-center p-3 border-b border-gray-100 last:border-b-0
        ${item.disabled ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer hover:bg-gray-50'}
        ${selected ? 'bg-blue-50 border-blue-200' : ''}
        transition-colors duration-150
      `}
    >
      {/* Selection indicator */}
      <div className={`w-4 h-4 mr-3 rounded border-2 flex items-center justify-center ${
        selected
          ? 'bg-blue-600 border-blue-600'
          : 'border-gray-300'
      }`}>
        {selected && <Check className="w-3 h-3 text-white" />}
      </div>

      {/* Avatar */}
      {item.avatar && (
        <img
          src={item.avatar}
          alt=""
          className="w-8 h-8 rounded-full mr-3"
        />
      )}

      {/* Content */}
      <div className="flex-1 min-w-0">
        <div className="font-medium text-gray-900 truncate">
          {item.label}
        </div>
        {item.description && (
          <div className="text-sm text-gray-600 truncate">
            {item.description}
          </div>
        )}
        {item.tags && item.tags.length > 0 && (
          <div className="flex flex-wrap gap-1 mt-1">
            {item.tags.slice(0, 3).map(tag => (
              <span
                key={tag}
                className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded"
              >
                {tag}
              </span>
            ))}
            {item.tags.length > 3 && (
              <span className="inline-block px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
                +{item.tags.length - 3}
              </span>
            )}
          </div>
        )}
      </div>

      {/* Category indicator */}
      {item.category && (
        <div className="ml-2 px-2 py-1 text-xs bg-gray-100 text-gray-700 rounded">
          {item.category}
        </div>
      )}
    </div>
  );
}

// Filter control component
interface FilterControlProps {
  filter: TransferListFilter;
  value: any;
  onChange: (value: any) => void;
}

function FilterControl({ filter, value, onChange }: FilterControlProps) {
  switch (filter.type) {
    case 'text':
      return (
        <input
          type="text"
          placeholder={filter.placeholder || `Filter by ${filter.label.toLowerCase()}...`}
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        />
      );

    case 'select':
      return (
        <select
          value={value || ''}
          onChange={(e) => onChange(e.target.value)}
          className="w-full px-3 py-2 text-sm border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
        >
          <option value="">All {filter.label}</option>
          {filter.options?.map(option => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      );

    case 'multiSelect':
      return (
        <div className="space-y-2">
          <label className="text-sm font-medium text-gray-700">{filter.label}</label>
          <div className="space-y-1 max-h-32 overflow-y-auto">
            {filter.options?.map(option => (
              <label key={option.value} className="flex items-center">
                <input
                  type="checkbox"
                  checked={Array.isArray(value) && value.includes(option.value)}
                  onChange={(e) => {
                    const currentValue = Array.isArray(value) ? value : [];
                    if (e.target.checked) {
                      onChange([...currentValue, option.value]);
                    } else {
                      onChange(currentValue.filter((v: any) => v !== option.value));
                    }
                  }}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">{option.label}</span>
              </label>
            ))}
          </div>
        </div>
      );

    default:
      return null;
  }
}