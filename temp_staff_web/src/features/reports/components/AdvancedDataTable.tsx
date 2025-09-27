import React, { useState, useMemo } from 'react';
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  createColumnHelper,
  SortingState,
  ColumnFiltersState,
  ColumnOrderState,
  VisibilityState,
} from '@tanstack/react-table';
import {
  DndContext,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
  DragEndEvent,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  horizontalListSortingStrategy,
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  ChevronDown,
  ChevronUp,
  Search,
  Eye,
  EyeOff,
  RotateCcw,
  Save,
  Filter,
  Download,
  Settings,
  GripVertical,
  ArrowUpDown,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';

// Types
interface ReportData {
  id: string;
  name: string;
  type: string;
  status: 'active' | 'pending' | 'completed' | 'error';
  priority: 'Low' | 'Medium' | 'High' | 'Critical';
  value: number;
  change: number;
  user: string;
  date: string;
  category: string;
}

// Sample data
const sampleData: ReportData[] = [
  {
    id: '1',
    name: 'Q1 Financial Report',
    type: 'Financial',
    status: 'completed',
    priority: 'High',
    value: 45000,
    change: 12.5,
    user: 'Maria Santos',
    date: '2024-01-15',
    category: 'Finance',
  },
  {
    id: '2',
    name: 'Student Analytics Dashboard',
    type: 'Academic',
    status: 'active',
    priority: 'Medium',
    value: 32000,
    change: -3.2,
    user: 'James Wilson',
    date: '2024-01-14',
    category: 'Academic',
  },
  {
    id: '3',
    name: 'Enrollment Trends Report',
    type: 'Academic',
    status: 'pending',
    priority: 'High',
    value: 28000,
    change: 8.7,
    user: 'Sarah Kim',
    date: '2024-01-13',
    category: 'Academic',
  },
  {
    id: '4',
    name: 'Payment Processing Summary',
    type: 'Financial',
    status: 'active',
    priority: 'Critical',
    value: 67000,
    change: 15.3,
    user: 'David Chen',
    date: '2024-01-12',
    category: 'Finance',
  },
  {
    id: '5',
    name: 'System Performance Report',
    type: 'Technical',
    status: 'error',
    priority: 'Low',
    value: 23000,
    change: -1.8,
    user: 'Lisa Wang',
    date: '2024-01-11',
    category: 'Operations',
  },
];

// Draggable Column Header Component
function DraggableColumnHeader({
  column,
  table,
}: {
  column: any;
  table: any;
}) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: column.id,
  });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.8 : 1,
  };

  return (
    <th
      ref={setNodeRef}
      style={style}
      className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50 border-b border-gray-200 relative group hover:bg-gray-100"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab hover:cursor-grabbing p-1 rounded hover:bg-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <GripVertical className="h-4 w-4 text-gray-400" />
          </div>
          <div
            className="flex items-center gap-1 cursor-pointer select-none"
            onClick={column.getToggleSortingHandler()}
          >
            <span className="font-semibold">
              {flexRender(column.columnDef.header, column.getContext())}
            </span>
            {column.getIsSorted() ? (
              column.getIsSorted() === 'desc' ? (
                <ChevronDown className="h-4 w-4" />
              ) : (
                <ChevronUp className="h-4 w-4" />
              )
            ) : (
              <ArrowUpDown className="h-3 w-3 opacity-0 group-hover:opacity-50" />
            )}
          </div>
        </div>
        {column.getCanFilter() && (
          <div className="ml-2">
            <Filter className="h-3 w-3 text-gray-400" />
          </div>
        )}
      </div>
    </th>
  );
}

const AdvancedDataTable: React.FC = () => {
  const [data] = useState<ReportData[]>(sampleData);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const columnHelper = createColumnHelper<ReportData>();

  const columns = useMemo(
    () => [
      columnHelper.accessor('name', {
        header: 'Report Name',
        cell: (info) => (
          <div className="font-medium text-gray-900 max-w-xs truncate">
            {info.getValue()}
          </div>
        ),
      }),
      columnHelper.accessor('type', {
        header: 'Type',
        cell: (info) => (
          <span className="text-sm text-gray-600">{info.getValue()}</span>
        ),
      }),
      columnHelper.accessor('status', {
        header: 'Status',
        cell: (info) => {
          const status = info.getValue();
          const statusColors = {
            active: 'bg-green-100 text-green-800',
            pending: 'bg-yellow-100 text-yellow-800',
            completed: 'bg-blue-100 text-blue-800',
            error: 'bg-red-100 text-red-800',
          };
          return (
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                statusColors[status]
              }`}
            >
              {status}
            </span>
          );
        },
      }),
      columnHelper.accessor('priority', {
        header: 'Priority',
        cell: (info) => {
          const priority = info.getValue();
          const priorityColors = {
            Low: 'bg-gray-100 text-gray-800',
            Medium: 'bg-blue-100 text-blue-800',
            High: 'bg-orange-100 text-orange-800',
            Critical: 'bg-red-100 text-red-800',
          };
          return (
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                priorityColors[priority]
              }`}
            >
              {priority}
            </span>
          );
        },
      }),
      columnHelper.accessor('value', {
        header: 'Value',
        cell: (info) => (
          <div className="font-medium text-gray-900">
            ${info.getValue().toLocaleString()}
          </div>
        ),
      }),
      columnHelper.accessor('change', {
        header: 'Change',
        cell: (info) => {
          const change = info.getValue();
          return (
            <div
              className={`font-medium ${
                change >= 0 ? 'text-green-600' : 'text-red-600'
              }`}
            >
              {change >= 0 ? '+' : ''}{change}%
            </div>
          );
        },
      }),
      columnHelper.accessor('user', {
        header: 'Created By',
        cell: (info) => (
          <div className="text-sm text-gray-600">{info.getValue()}</div>
        ),
      }),
      columnHelper.accessor('date', {
        header: 'Date',
        cell: (info) => (
          <div className="text-sm text-gray-600">
            {new Date(info.getValue()).toLocaleDateString()}
          </div>
        ),
      }),
    ],
    [columnHelper]
  );

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      columnVisibility,
      columnOrder,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onColumnVisibilityChange: setColumnVisibility,
    onColumnOrderChange: setColumnOrder,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
  });

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;

    if (active && over && active.id !== over.id) {
      setColumnOrder((columnOrder) => {
        const oldIndex = columnOrder.indexOf(active.id as string);
        const newIndex = columnOrder.indexOf(over.id as string);
        return arrayMove(columnOrder, oldIndex, newIndex);
      });
    }
  };

  const resetTable = () => {
    setSorting([]);
    setColumnFilters([]);
    setColumnVisibility({});
    setColumnOrder([]);
    setGlobalFilter('');
    table.resetPagination();
  };

  const stats = [
    {
      name: 'Total Reports',
      value: data.length,
      change: '+12%',
      changeType: 'positive' as const,
    },
    {
      name: 'Active Reports',
      value: data.filter((d) => d.status === 'active').length,
      change: '+5%',
      changeType: 'positive' as const,
    },
    {
      name: 'Total Value',
      value: `$${data.reduce((sum, d) => sum + d.value, 0).toLocaleString()}`,
      change: '+8%',
      changeType: 'positive' as const,
    },
    {
      name: 'Avg Change',
      value: `${(data.reduce((sum, d) => sum + d.change, 0) / data.length).toFixed(1)}%`,
      change: '-2%',
      changeType: 'negative' as const,
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🚀 TanStack Table + DND Kit Demo
          </h1>
          <p className="text-gray-600">
            Professional data table with drag & drop column reordering, sorting, filtering, and more
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => (
            <div key={stat.name} className="bg-white rounded-lg shadow p-6">
              <div className="flex items-center">
                <div className="flex-1">
                  <p className="text-sm font-medium text-gray-600">{stat.name}</p>
                  <p className="text-2xl font-bold text-gray-900">{stat.value}</p>
                  <p
                    className={`text-sm ${
                      stat.changeType === 'positive'
                        ? 'text-green-600'
                        : 'text-red-600'
                    }`}
                  >
                    {stat.change} from last month
                  </p>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Controls */}
        <div className="bg-white rounded-lg shadow mb-6 p-6">
          <div className="flex flex-col lg:flex-row gap-4 items-start lg:items-center justify-between">
            {/* Search */}
            <div className="flex-1 max-w-md">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-gray-400 h-4 w-4" />
                <input
                  type="text"
                  placeholder="Search all columns..."
                  value={globalFilter ?? ''}
                  onChange={(e) => setGlobalFilter(e.target.value)}
                  className="pl-10 pr-4 py-2 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 w-full"
                />
              </div>
            </div>

            {/* Action Buttons */}
            <div className="flex gap-2 flex-wrap">
              <button
                onClick={resetTable}
                className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Reset
              </button>
              
              <button className="inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <Download className="h-4 w-4 mr-2" />
                Export
              </button>
              
              <button className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500">
                <Save className="h-4 w-4 mr-2" />
                Save Layout
              </button>
            </div>
          </div>

          {/* Column Visibility Controls */}
          <div className="mt-6 border-t pt-4">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-medium text-gray-900">Column Visibility</h3>
              <div className="flex gap-2">
                <button
                  onClick={() => table.toggleAllColumnsVisible(true)}
                  className="text-sm text-blue-600 hover:text-blue-800"
                >
                  Show All
                </button>
                <span className="text-gray-300">|</span>
                <button
                  onClick={() => table.toggleAllColumnsVisible(false)}
                  className="text-sm text-gray-600 hover:text-gray-800"
                >
                  Hide All
                </button>
              </div>
            </div>
            <div className="flex flex-wrap gap-4">
              {table.getAllColumns().map((column) => (
                <label key={column.id} className="flex items-center">
                  <input
                    type="checkbox"
                    checked={column.getIsVisible()}
                    onChange={column.getToggleVisibilityHandler()}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
                  />
                  <span className="text-sm text-gray-700">
                    {typeof column.columnDef.header === 'string' 
                      ? column.columnDef.header 
                      : column.id}
                  </span>
                </label>
              ))}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Interactive Data Table
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Drag column headers to reorder • Click headers to sort • Use search to filter
            </p>
          </div>

          <DndContext
            sensors={sensors}
            collisionDetection={closestCenter}
            onDragEnd={handleDragEnd}
          >
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200">
                <thead>
                  <SortableContext
                    items={table.getVisibleLeafColumns().map((c) => c.id)}
                    strategy={horizontalListSortingStrategy}
                  >
                    <tr>
                      {table.getVisibleLeafColumns().map((column) => (
                        <DraggableColumnHeader
                          key={column.id}
                          column={column}
                          table={table}
                        />
                      ))}
                    </tr>
                  </SortableContext>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {table.getRowModel().rows.map((row) => (
                    <tr key={row.id} className="hover:bg-gray-50">
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-6 py-4 whitespace-nowrap">
                          {flexRender(cell.column.columnDef.cell, cell.getContext())}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </DndContext>

          {/* Pagination */}
          <div className="px-6 py-3 flex items-center justify-between border-t border-gray-200 bg-gray-50">
            <div className="flex-1 flex justify-between items-center">
              <div>
                <p className="text-sm text-gray-700">
                  Showing{' '}
                  <span className="font-medium">
                    {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1}
                  </span>{' '}
                  to{' '}
                  <span className="font-medium">
                    {Math.min(
                      (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
                      table.getFilteredRowModel().rows.length
                    )}
                  </span>{' '}
                  of{' '}
                  <span className="font-medium">{table.getFilteredRowModel().rows.length}</span> results
                </p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  onClick={() => table.previousPage()}
                  disabled={!table.getCanPreviousPage()}
                  className="relative inline-flex items-center px-2 py-2 rounded-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronLeft className="h-5 w-5" />
                </button>
                <span className="text-sm text-gray-700">
                  Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
                </span>
                <button
                  onClick={() => table.nextPage()}
                  disabled={!table.getCanNextPage()}
                  className="relative inline-flex items-center px-2 py-2 rounded-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  <ChevronRight className="h-5 w-5" />
                </button>
              </div>
            </div>
          </div>
        </div>

        {/* Features */}
        <div className="mt-8 bg-gradient-to-r from-blue-500 to-purple-600 rounded-lg p-8 text-white">
          <h3 className="text-xl font-bold mb-6">✨ Features Demonstrated</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <Settings className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Drag & Drop Columns</h4>
                <p className="text-blue-100 text-sm">Reorder columns by dragging headers</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <ArrowUpDown className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Multi-Column Sorting</h4>
                <p className="text-blue-100 text-sm">Click headers to sort, hold Shift for multi-sort</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Search className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Global Filtering</h4>
                <p className="text-blue-100 text-sm">Search across all columns simultaneously</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Eye className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Column Visibility</h4>
                <p className="text-blue-100 text-sm">Show/hide columns dynamically</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Filter className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Advanced Filtering</h4>
                <p className="text-blue-100 text-sm">Built-in column-specific filters</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <ChevronLeft className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Pagination</h4>
                <p className="text-blue-100 text-sm">Navigate through large datasets efficiently</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AdvancedDataTable;