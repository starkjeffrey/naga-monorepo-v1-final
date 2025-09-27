/**
 * DataGrid Toolbar Component
 * Handles search, bulk actions, import/export, and presets
 */

import React, { useState, useRef } from 'react';
import {
  Search,
  Download,
  Upload,
  Filter,
  RefreshCw,
  MoreHorizontal,
  Save,
  FolderOpen,
  X,
  FileText,
  FileSpreadsheet,
  FilePlus,
  Trash2,
  Settings
} from 'lucide-react';
import {
  DataGridBulkAction,
  DataGridExportOptions,
  SavedFilterPreset,
  DataGridFilter
} from '../types';

interface DataGridToolbarProps<T> {
  // Search
  searchable?: boolean;
  searchQuery: string;
  onSearchChange: (query: string) => void;

  // Selection and bulk actions
  selectedCount: number;
  totalCount: number;
  bulkActions?: DataGridBulkAction<T>[];
  selectedRows: T[];
  onClearSelection: () => void;
  onSelectAll: () => void;

  // Import/Export
  exportable?: boolean;
  importable?: boolean;
  onExport?: (options: DataGridExportOptions) => void;
  onImport?: (file: File) => void;
  onDownloadTemplate?: () => void;

  // Filter presets
  savedPresets?: SavedFilterPreset[];
  currentFilters: DataGridFilter[];
  onPresetSave?: (preset: Omit<SavedFilterPreset, 'id' | 'createdAt'>) => void;
  onPresetLoad?: (preset: SavedFilterPreset) => void;
  onPresetDelete?: (presetId: string) => void;

  // Refresh
  onRefresh?: () => void;
  loading?: boolean;

  // Misc
  title?: string;
  subtitle?: string;
  className?: string;
}

export function DataGridToolbar<T>({
  searchable = true,
  searchQuery,
  onSearchChange,
  selectedCount,
  totalCount,
  bulkActions = [],
  selectedRows,
  onClearSelection,
  onSelectAll,
  exportable = true,
  importable = false,
  onExport,
  onImport,
  onDownloadTemplate,
  savedPresets = [],
  currentFilters,
  onPresetSave,
  onPresetLoad,
  onPresetDelete,
  onRefresh,
  loading = false,
  title,
  subtitle,
  className = ''
}: DataGridToolbarProps<T>) {
  const [showExportMenu, setShowExportMenu] = useState(false);
  const [showPresetMenu, setShowPresetMenu] = useState(false);
  const [showSavePresetDialog, setShowSavePresetDialog] = useState(false);
  const [presetName, setPresetName] = useState('');

  const fileInputRef = useRef<HTMLInputElement>(null);

  const hasSelection = selectedCount > 0;
  const hasFilters = currentFilters.length > 0;

  const handleExport = (format: 'csv' | 'excel' | 'pdf') => {
    if (onExport) {
      onExport({
        format,
        filename: `export-${new Date().toISOString().split('T')[0]}`,
        selectedOnly: hasSelection,
        includeHeaders: true
      });
    }
    setShowExportMenu(false);
  };

  const handleImport = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (file && onImport) {
      onImport(file);
    }
    // Reset input
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleSavePreset = () => {
    if (presetName.trim() && onPresetSave) {
      onPresetSave({
        name: presetName.trim(),
        filters: currentFilters,
        sorts: [], // Would need to be passed as prop
        isDefault: false,
        isShared: false
      });
      setPresetName('');
      setShowSavePresetDialog(false);
    }
  };

  const executeBulkAction = (action: DataGridBulkAction<T>) => {
    if (action.requiresConfirmation) {
      const confirmed = window.confirm(
        action.confirmationMessage ||
        `Are you sure you want to ${action.label.toLowerCase()} ${selectedCount} items?`
      );
      if (!confirmed) return;
    }

    action.onClick(selectedRows);
  };

  const ExportMenu = () => (
    <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-48">
      <button
        onClick={() => handleExport('csv')}
        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
      >
        <FileText className="w-4 h-4 mr-2" />
        Export as CSV
      </button>
      <button
        onClick={() => handleExport('excel')}
        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
      >
        <FileSpreadsheet className="w-4 h-4 mr-2" />
        Export as Excel
      </button>
      <button
        onClick={() => handleExport('pdf')}
        className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
      >
        <FileText className="w-4 h-4 mr-2" />
        Export as PDF
      </button>
      {hasSelection && (
        <>
          <hr className="my-1" />
          <div className="px-4 py-2 text-xs text-gray-500">
            Export selected ({selectedCount} items)
          </div>
        </>
      )}
    </div>
  );

  const PresetMenu = () => (
    <div className="absolute top-full right-0 mt-1 bg-white border border-gray-200 rounded-lg shadow-lg py-1 z-50 min-w-64">
      {savedPresets.length > 0 && (
        <>
          <div className="px-4 py-2 text-xs font-medium text-gray-500 uppercase">
            Saved Presets
          </div>
          {savedPresets.map(preset => (
            <div key={preset.id} className="flex items-center px-4 py-2 hover:bg-gray-100">
              <button
                onClick={() => {
                  onPresetLoad?.(preset);
                  setShowPresetMenu(false);
                }}
                className="flex-1 text-left text-sm text-gray-700 flex items-center"
              >
                <FolderOpen className="w-4 h-4 mr-2" />
                {preset.name}
                {preset.isDefault && (
                  <span className="ml-2 text-xs text-blue-600">(Default)</span>
                )}
              </button>
              <button
                onClick={() => onPresetDelete?.(preset.id)}
                className="p-1 text-gray-400 hover:text-red-600"
              >
                <Trash2 className="w-3 h-3" />
              </button>
            </div>
          ))}
          <hr className="my-1" />
        </>
      )}

      {hasFilters && (
        <button
          onClick={() => {
            setShowPresetMenu(false);
            setShowSavePresetDialog(true);
          }}
          className="w-full px-4 py-2 text-left text-sm text-gray-700 hover:bg-gray-100 flex items-center"
        >
          <Save className="w-4 h-4 mr-2" />
          Save Current Filters
        </button>
      )}
    </div>
  );

  const SavePresetDialog = () => (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-96">
        <h3 className="text-lg font-medium text-gray-900 mb-4">Save Filter Preset</h3>
        <input
          type="text"
          placeholder="Enter preset name..."
          value={presetName}
          onChange={(e) => setPresetName(e.target.value)}
          className="w-full px-3 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500"
          autoFocus
        />
        <div className="mt-4 flex justify-end space-x-2">
          <button
            onClick={() => {
              setShowSavePresetDialog(false);
              setPresetName('');
            }}
            className="px-4 py-2 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
          >
            Cancel
          </button>
          <button
            onClick={handleSavePreset}
            disabled={!presetName.trim()}
            className="px-4 py-2 text-sm text-white bg-blue-600 rounded-md hover:bg-blue-700 disabled:opacity-50"
          >
            Save Preset
          </button>
        </div>
      </div>
    </div>
  );

  return (
    <>
      <div className={`bg-white border-b border-gray-200 px-6 py-4 ${className}`}>
        {/* Header section */}
        {(title || subtitle) && (
          <div className="mb-4">
            {title && <h2 className="text-lg font-medium text-gray-900">{title}</h2>}
            {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
          </div>
        )}

        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-3 sm:space-y-0">
          {/* Left side - Search and stats */}
          <div className="flex items-center space-x-4">
            {searchable && (
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search..."
                  value={searchQuery}
                  onChange={(e) => onSearchChange(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-blue-500 focus:border-blue-500 w-64"
                />
              </div>
            )}

            <div className="text-sm text-gray-600">
              {selectedCount > 0 ? (
                <span className="font-medium">
                  {selectedCount} of {totalCount} selected
                </span>
              ) : (
                <span>{totalCount} items</span>
              )}
            </div>

            {hasFilters && (
              <div className="flex items-center text-sm text-blue-600">
                <Filter className="w-4 h-4 mr-1" />
                {currentFilters.length} filter{currentFilters.length !== 1 ? 's' : ''} applied
              </div>
            )}
          </div>

          {/* Right side - Actions */}
          <div className="flex items-center space-x-2">
            {/* Selection actions */}
            {hasSelection && (
              <>
                <div className="flex items-center space-x-2 mr-4">
                  {bulkActions.map(action => (
                    <button
                      key={action.id}
                      onClick={() => executeBulkAction(action)}
                      disabled={action.disabled?.(selectedRows)}
                      className={`
                        px-3 py-1.5 text-sm rounded-md flex items-center space-x-1
                        ${action.variant === 'danger'
                          ? 'text-red-700 bg-red-100 hover:bg-red-200'
                          : 'text-blue-700 bg-blue-100 hover:bg-blue-200'
                        }
                        disabled:opacity-50 disabled:cursor-not-allowed
                      `}
                    >
                      {action.icon}
                      <span>{action.label}</span>
                    </button>
                  ))}

                  <button
                    onClick={onClearSelection}
                    className="p-1.5 text-gray-400 hover:text-gray-600"
                    title="Clear selection"
                  >
                    <X className="w-4 h-4" />
                  </button>
                </div>
              </>
            )}

            {/* Select All */}
            {!hasSelection && totalCount > 0 && (
              <button
                onClick={onSelectAll}
                className="px-3 py-1.5 text-sm text-gray-700 bg-gray-100 rounded-md hover:bg-gray-200"
              >
                Select All
              </button>
            )}

            {/* Import */}
            {importable && (
              <>
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".csv,.xlsx,.xls"
                  onChange={handleImport}
                  className="hidden"
                />
                <button
                  onClick={() => fileInputRef.current?.click()}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
                  title="Import data"
                >
                  <Upload className="w-4 h-4" />
                </button>
                {onDownloadTemplate && (
                  <button
                    onClick={onDownloadTemplate}
                    className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
                    title="Download import template"
                  >
                    <FilePlus className="w-4 h-4" />
                  </button>
                )}
              </>
            )}

            {/* Export */}
            {exportable && onExport && (
              <div className="relative">
                <button
                  onClick={() => setShowExportMenu(!showExportMenu)}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
                  title="Export data"
                >
                  <Download className="w-4 h-4" />
                </button>
                {showExportMenu && <ExportMenu />}
              </div>
            )}

            {/* Filter Presets */}
            {(savedPresets.length > 0 || hasFilters) && (
              <div className="relative">
                <button
                  onClick={() => setShowPresetMenu(!showPresetMenu)}
                  className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md"
                  title="Filter presets"
                >
                  <Settings className="w-4 h-4" />
                </button>
                {showPresetMenu && <PresetMenu />}
              </div>
            )}

            {/* Refresh */}
            {onRefresh && (
              <button
                onClick={onRefresh}
                disabled={loading}
                className="p-2 text-gray-600 hover:text-gray-900 hover:bg-gray-100 rounded-md disabled:opacity-50"
                title="Refresh data"
              >
                <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Click outside handlers */}
      {showExportMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowExportMenu(false)}
        />
      )}

      {showPresetMenu && (
        <div
          className="fixed inset-0 z-40"
          onClick={() => setShowPresetMenu(false)}
        />
      )}

      {/* Save preset dialog */}
      {showSavePresetDialog && <SavePresetDialog />}
    </>
  );
}