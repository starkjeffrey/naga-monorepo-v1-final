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
  User,
  GraduationCap,
  Calendar,
  MapPin,
  Mail,
  Phone,
  UserCheck,
  Users,
  BookOpen,
  Clock,
} from 'lucide-react';

// Student Information Interface (matches your StudentProfile + Person models)
interface StudentInformation {
  id: string;
  // Person data
  person_id: number;
  unique_id: string;
  full_name: string;
  family_name: string;
  personal_name: string;
  khmer_name: string;
  preferred_gender: 'M' | 'F' | 'N' | 'X';
  school_email?: string;
  personal_email?: string;
  date_of_birth?: string;
  birth_province?: string;
  citizenship: string;
  age?: number;
  current_photo_url?: string;
  
  // Student Profile data
  student_id: number;
  formatted_student_id: string;
  legacy_ipk?: number;
  is_monk: boolean;
  is_transfer_student: boolean;
  current_status: 'ACTIVE' | 'INACTIVE' | 'GRADUATED' | 'DROPPED' | 'SUSPENDED' | 'TRANSFERRED' | 'FROZEN' | 'UNKNOWN';
  study_time_preference: 'morning' | 'afternoon' | 'evening';
  last_enrollment_date?: string;
  is_student_active: boolean;
  
  // Academic data
  declared_major_name?: string;
  enrollment_history_major_name?: string;
  current_gpa?: number;
  total_credits?: number;
  enrollment_year?: number;
  expected_graduation?: string;
  
  // Additional metadata
  created_at: string;
  updated_at: string;
}

// Sample data based on your actual model structure
const sampleStudentData: StudentInformation[] = [
  {
    id: '1',
    person_id: 1001,
    unique_id: 'uuid-001-student',
    full_name: 'CHEA SOKHA',
    family_name: 'CHEA',
    personal_name: 'SOKHA',
    khmer_name: 'ជា សុខា',
    preferred_gender: 'M',
    school_email: 'chea.sokha@naga.edu.kh',
    personal_email: 'sokha.chea@gmail.com',
    date_of_birth: '2001-03-15',
    birth_province: 'Phnom Penh',
    citizenship: 'KH',
    age: 23,
    current_photo_url: '/api/photos/student_001.jpg',
    student_id: 18001,
    formatted_student_id: '18001',
    legacy_ipk: 12345,
    is_monk: false,
    is_transfer_student: false,
    current_status: 'ACTIVE',
    study_time_preference: 'evening',
    last_enrollment_date: '2024-01-10',
    is_student_active: true,
    declared_major_name: 'Computer Science',
    enrollment_history_major_name: 'Computer Science',
    current_gpa: 3.75,
    total_credits: 45,
    enrollment_year: 2022,
    expected_graduation: '2025-12-01',
    created_at: '2022-09-01T08:00:00Z',
    updated_at: '2024-01-15T10:30:00Z',
  },
  {
    id: '2',
    person_id: 1002,
    unique_id: 'uuid-002-student',
    full_name: 'LIM SREYPICH',
    family_name: 'LIM',
    personal_name: 'SREYPICH',
    khmer_name: 'លឹម ស្រីពេជ្រ',
    preferred_gender: 'F',
    school_email: 'lim.sreypich@naga.edu.kh',
    personal_email: 'sreypich.lim@outlook.com',
    date_of_birth: '2000-07-22',
    birth_province: 'Siem Reap',
    citizenship: 'KH',
    age: 24,
    student_id: 18002,
    formatted_student_id: '18002',
    legacy_ipk: 12346,
    is_monk: false,
    is_transfer_student: true,
    current_status: 'ACTIVE',
    study_time_preference: 'morning',
    last_enrollment_date: '2024-01-10',
    is_student_active: true,
    declared_major_name: 'Business Administration',
    enrollment_history_major_name: 'Economics',
    current_gpa: 3.92,
    total_credits: 78,
    enrollment_year: 2021,
    expected_graduation: '2025-06-01',
    created_at: '2021-08-15T09:15:00Z',
    updated_at: '2024-01-12T14:20:00Z',
  },
  {
    id: '3',
    person_id: 1003,
    unique_id: 'uuid-003-student',
    full_name: 'PREAH VICHEKA',
    family_name: 'PREAH',
    personal_name: 'VICHEKA',
    khmer_name: 'ព្រះ វិជេកា',
    preferred_gender: 'M',
    school_email: 'preah.vicheka@naga.edu.kh',
    date_of_birth: '1999-11-08',
    birth_province: 'Battambang',
    citizenship: 'KH',
    age: 25,
    student_id: 17845,
    formatted_student_id: '17845',
    legacy_ipk: 11987,
    is_monk: true,
    is_transfer_student: false,
    current_status: 'ACTIVE',
    study_time_preference: 'afternoon',
    last_enrollment_date: '2024-01-10',
    is_student_active: true,
    declared_major_name: 'Buddhist Studies',
    enrollment_history_major_name: 'Buddhist Studies',
    current_gpa: 4.0,
    total_credits: 92,
    enrollment_year: 2020,
    expected_graduation: '2025-03-01',
    created_at: '2020-09-01T07:00:00Z',
    updated_at: '2024-01-10T11:45:00Z',
  },
  {
    id: '4',
    person_id: 1004,
    unique_id: 'uuid-004-student',
    full_name: 'NGUYEN THI LINH',
    family_name: 'NGUYEN THI',
    personal_name: 'LINH',
    khmer_name: '',
    preferred_gender: 'F',
    school_email: 'nguyen.linh@naga.edu.kh',
    personal_email: 'linh.nguyen@yahoo.com',
    date_of_birth: '2002-01-30',
    birth_province: 'International',
    citizenship: 'VN',
    age: 22,
    student_id: 18125,
    formatted_student_id: '18125',
    is_monk: false,
    is_transfer_student: true,
    current_status: 'ACTIVE',
    study_time_preference: 'evening',
    last_enrollment_date: '2023-09-01',
    is_student_active: true,
    declared_major_name: 'International Relations',
    enrollment_history_major_name: 'International Relations',
    current_gpa: 3.85,
    total_credits: 32,
    enrollment_year: 2023,
    expected_graduation: '2026-12-01',
    created_at: '2023-08-20T10:00:00Z',
    updated_at: '2024-01-08T16:30:00Z',
  },
  {
    id: '5',
    person_id: 1005,
    unique_id: 'uuid-005-student',
    full_name: 'KONG PISACH',
    family_name: 'KONG',
    personal_name: 'PISACH',
    khmer_name: 'គង ពិសាច',
    preferred_gender: 'M',
    school_email: 'kong.pisach@naga.edu.kh',
    personal_email: 'pisach.kong@gmail.com',
    date_of_birth: '2001-12-05',
    birth_province: 'Kandal',
    citizenship: 'KH',
    age: 22,
    student_id: 18089,
    formatted_student_id: '18089',
    legacy_ipk: 12789,
    is_monk: false,
    is_transfer_student: false,
    current_status: 'SUSPENDED',
    study_time_preference: 'morning',
    last_enrollment_date: '2023-12-15',
    is_student_active: false,
    declared_major_name: 'Mechanical Engineering',
    enrollment_history_major_name: 'Mechanical Engineering',
    current_gpa: 2.45,
    total_credits: 68,
    enrollment_year: 2022,
    expected_graduation: '2026-06-01',
    created_at: '2022-08-25T14:15:00Z',
    updated_at: '2023-12-20T09:45:00Z',
  },
  {
    id: '6',
    person_id: 1006,
    unique_id: 'uuid-006-student',
    full_name: 'SOM CHANMONY',
    family_name: 'SOM',
    personal_name: 'CHANMONY',
    khmer_name: 'សុំ ច័ន្ទមុនី',
    preferred_gender: 'F',
    school_email: 'som.chanmony@naga.edu.kh',
    date_of_birth: '1998-06-18',
    birth_province: 'Takeo',
    citizenship: 'KH',
    age: 26,
    student_id: 17234,
    formatted_student_id: '17234',
    legacy_ipk: 11456,
    is_monk: false,
    is_transfer_student: false,
    current_status: 'GRADUATED',
    study_time_preference: 'evening',
    last_enrollment_date: '2023-12-01',
    is_student_active: false,
    declared_major_name: 'English Literature',
    enrollment_history_major_name: 'English Literature',
    current_gpa: 3.68,
    total_credits: 120,
    enrollment_year: 2019,
    expected_graduation: '2023-12-01',
    created_at: '2019-09-01T08:30:00Z',
    updated_at: '2023-12-15T17:00:00Z',
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
      className="px-4 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider bg-gray-50 border-b border-gray-200 relative group hover:bg-gray-100"
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div
            {...attributes}
            {...listeners}
            className="cursor-grab hover:cursor-grabbing p-1 rounded hover:bg-gray-200 opacity-0 group-hover:opacity-100 transition-opacity"
          >
            <GripVertical className="h-3 w-3 text-gray-400" />
          </div>
          <div
            className="flex items-center gap-1 cursor-pointer select-none"
            onClick={column.getToggleSortingHandler()}
          >
            <span className="font-semibold text-xs">
              {flexRender(column.columnDef.header, column.getContext())}
            </span>
            {column.getIsSorted() ? (
              column.getIsSorted() === 'desc' ? (
                <ChevronDown className="h-3 w-3" />
              ) : (
                <ChevronUp className="h-3 w-3" />
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

const StudentInformationTable: React.FC = () => {
  const [data] = useState<StudentInformation[]>(sampleStudentData);
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({
    unique_id: false,
    legacy_ipk: false,
    created_at: false,
    updated_at: false,
  });
  const [columnOrder, setColumnOrder] = useState<ColumnOrderState>([]);
  const [globalFilter, setGlobalFilter] = useState('');

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  const columnHelper = createColumnHelper<StudentInformation>();

  const columns = useMemo(
    () => [
      columnHelper.accessor('formatted_student_id', {
        header: 'Student ID',
        size: 100,
        cell: (info) => (
          <div className="font-mono text-sm font-semibold text-blue-700">
            {info.getValue()}
          </div>
        ),
      }),
      columnHelper.accessor('current_photo_url', {
        header: 'Photo',
        size: 60,
        enableSorting: false,
        cell: (info) => (
          <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center overflow-hidden">
            {info.getValue() ? (
              <img
                src={info.getValue()}
                alt="Student"
                className="w-full h-full object-cover"
                onError={(e) => {
                  (e.target as HTMLImageElement).style.display = 'none';
                  (e.target as HTMLElement).nextElementSibling?.classList.remove('hidden');
                }}
              />
            ) : null}
            <User className="h-4 w-4 text-gray-400" />
          </div>
        ),
      }),
      columnHelper.accessor('full_name', {
        header: 'Full Name',
        size: 180,
        cell: (info) => (
          <div>
            <div className="font-semibold text-gray-900 text-sm">
              {info.getValue()}
            </div>
            {info.row.original.khmer_name && (
              <div className="text-xs text-gray-500 mt-1">
                {info.row.original.khmer_name}
              </div>
            )}
          </div>
        ),
      }),
      columnHelper.accessor('preferred_gender', {
        header: 'Gender',
        size: 80,
        cell: (info) => {
          const gender = info.getValue();
          const genderMap = {
            M: 'Male',
            F: 'Female',
            N: 'Non-Binary',
            X: 'Prefer Not to Say',
          };
          return (
            <span className="text-sm text-gray-600">
              {genderMap[gender] || gender}
            </span>
          );
        },
      }),
      columnHelper.accessor('age', {
        header: 'Age',
        size: 70,
        cell: (info) => (
          <span className="text-sm font-medium text-gray-700">
            {info.getValue() || 'N/A'}
          </span>
        ),
      }),
      columnHelper.accessor('current_status', {
        header: 'Status',
        size: 120,
        cell: (info) => {
          const status = info.getValue();
          const statusColors = {
            ACTIVE: 'bg-green-100 text-green-800',
            INACTIVE: 'bg-gray-100 text-gray-800',
            GRADUATED: 'bg-blue-100 text-blue-800',
            DROPPED: 'bg-red-100 text-red-800',
            SUSPENDED: 'bg-yellow-100 text-yellow-800',
            TRANSFERRED: 'bg-purple-100 text-purple-800',
            FROZEN: 'bg-indigo-100 text-indigo-800',
            UNKNOWN: 'bg-gray-100 text-gray-800',
          };
          return (
            <span
              className={`inline-flex items-center px-2 py-1 rounded-full text-xs font-medium ${
                statusColors[status] || statusColors.UNKNOWN
              }`}
            >
              {status}
            </span>
          );
        },
      }),
      columnHelper.accessor('is_monk', {
        header: 'Monk',
        size: 80,
        cell: (info) => (
          <div className="flex items-center justify-center">
            {info.getValue() ? (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-orange-100 text-orange-800">
                🙏 Monk
              </span>
            ) : (
              <span className="text-gray-400">-</span>
            )}
          </div>
        ),
      }),
      columnHelper.accessor('is_transfer_student', {
        header: 'Transfer',
        size: 90,
        cell: (info) => (
          <div className="flex items-center justify-center">
            {info.getValue() ? (
              <span className="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-blue-100 text-blue-800">
                Transfer
              </span>
            ) : (
              <span className="text-gray-400">-</span>
            )}
          </div>
        ),
      }),
      columnHelper.accessor('declared_major_name', {
        header: 'Major',
        size: 160,
        cell: (info) => (
          <div className="text-sm">
            <div className="font-medium text-gray-900">
              {info.getValue() || 'Undeclared'}
            </div>
            {info.row.original.enrollment_history_major_name &&
              info.row.original.enrollment_history_major_name !== info.getValue() && (
                <div className="text-xs text-gray-500 mt-1">
                  History: {info.row.original.enrollment_history_major_name}
                </div>
              )}
          </div>
        ),
      }),
      columnHelper.accessor('study_time_preference', {
        header: 'Study Time',
        size: 100,
        cell: (info) => {
          const preference = info.getValue();
          const prefMap = {
            morning: '🌅 Morning',
            afternoon: '☀️ Afternoon',
            evening: '🌙 Evening',
          };
          return (
            <span className="text-sm text-gray-600">
              {prefMap[preference] || preference}
            </span>
          );
        },
      }),
      columnHelper.accessor('current_gpa', {
        header: 'GPA',
        size: 80,
        cell: (info) => {
          const gpa = info.getValue();
          if (!gpa) return <span className="text-gray-400">-</span>;
          const gpaColor = gpa >= 3.5 ? 'text-green-600' : gpa >= 3.0 ? 'text-blue-600' : gpa >= 2.5 ? 'text-yellow-600' : 'text-red-600';
          return (
            <span className={`text-sm font-semibold ${gpaColor}`}>
              {gpa.toFixed(2)}
            </span>
          );
        },
      }),
      columnHelper.accessor('total_credits', {
        header: 'Credits',
        size: 80,
        cell: (info) => (
          <span className="text-sm font-medium text-gray-700">
            {info.getValue() || 0}
          </span>
        ),
      }),
      columnHelper.accessor('school_email', {
        header: 'School Email',
        size: 200,
        cell: (info) => (
          <div className="text-sm">
            {info.getValue() ? (
              <a
                href={`mailto:${info.getValue()}`}
                className="text-blue-600 hover:text-blue-800 hover:underline"
              >
                {info.getValue()}
              </a>
            ) : (
              <span className="text-gray-400">-</span>
            )}
          </div>
        ),
      }),
      columnHelper.accessor('birth_province', {
        header: 'Birth Province',
        size: 140,
        cell: (info) => (
          <span className="text-sm text-gray-600">
            {info.getValue() || 'Unknown'}
          </span>
        ),
      }),
      columnHelper.accessor('citizenship', {
        header: 'Citizenship',
        size: 100,
        cell: (info) => {
          const country = info.getValue();
          const flagMap: { [key: string]: string } = {
            KH: '🇰🇭',
            VN: '🇻🇳',
            TH: '🇹🇭',
            US: '🇺🇸',
            GB: '🇬🇧',
          };
          return (
            <span className="text-sm">
              {flagMap[country] || '🌍'} {country}
            </span>
          );
        },
      }),
      columnHelper.accessor('enrollment_year', {
        header: 'Entry Year',
        size: 100,
        cell: (info) => (
          <span className="text-sm font-medium text-gray-700">
            {info.getValue() || 'N/A'}
          </span>
        ),
      }),
      columnHelper.accessor('expected_graduation', {
        header: 'Expected Graduation',
        size: 140,
        cell: (info) => {
          const date = info.getValue();
          return (
            <span className="text-sm text-gray-600">
              {date ? new Date(date).toLocaleDateString() : 'N/A'}
            </span>
          );
        },
      }),
      columnHelper.accessor('unique_id', {
        header: 'UUID',
        size: 200,
        cell: (info) => (
          <span className="text-xs font-mono text-gray-500">
            {info.getValue()}
          </span>
        ),
      }),
      columnHelper.accessor('legacy_ipk', {
        header: 'Legacy IPK',
        size: 100,
        cell: (info) => (
          <span className="text-sm text-gray-600">
            {info.getValue() || 'N/A'}
          </span>
        ),
      }),
      columnHelper.accessor('created_at', {
        header: 'Created',
        size: 120,
        cell: (info) => (
          <span className="text-xs text-gray-500">
            {new Date(info.getValue()).toLocaleDateString()}
          </span>
        ),
      }),
      columnHelper.accessor('updated_at', {
        header: 'Updated',
        size: 120,
        cell: (info) => (
          <span className="text-xs text-gray-500">
            {new Date(info.getValue()).toLocaleDateString()}
          </span>
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
    initialState: {
      pagination: {
        pageSize: 10,
      },
    },
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
    setColumnVisibility({
      unique_id: false,
      legacy_ipk: false,
      created_at: false,
      updated_at: false,
    });
    setColumnOrder([]);
    setGlobalFilter('');
    table.resetPagination();
  };

  const stats = [
    {
      name: 'Total Students',
      value: data.length,
      change: '+5 this month',
      changeType: 'positive' as const,
      icon: Users,
      color: 'blue',
    },
    {
      name: 'Active Students',
      value: data.filter((d) => d.current_status === 'ACTIVE').length,
      change: '+3 this month',
      changeType: 'positive' as const,
      icon: UserCheck,
      color: 'green',
    },
    {
      name: 'Monks',
      value: data.filter((d) => d.is_monk).length,
      change: 'No change',
      changeType: 'neutral' as const,
      icon: User,
      color: 'orange',
    },
    {
      name: 'Avg GPA',
      value: (data.filter(d => d.current_gpa).reduce((sum, d) => sum + (d.current_gpa || 0), 0) / data.filter(d => d.current_gpa).length).toFixed(2),
      change: '+0.1 this term',
      changeType: 'positive' as const,
      icon: GraduationCap,
      color: 'purple',
    },
  ];

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            🎓 Student Information Management
          </h1>
          <p className="text-gray-600">
            Comprehensive student database with drag & drop columns, advanced filtering, and real-time data management
          </p>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {stats.map((stat) => {
            const Icon = stat.icon;
            const colorClasses = {
              blue: 'bg-blue-500',
              green: 'bg-green-500',
              orange: 'bg-orange-500',
              purple: 'bg-purple-500',
            };
            return (
              <div key={stat.name} className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center">
                  <div className="flex-shrink-0">
                    <div className={`w-8 h-8 ${colorClasses[stat.color]} rounded-lg flex items-center justify-center`}>
                      <Icon className="h-5 w-5 text-white" />
                    </div>
                  </div>
                  <div className="ml-5 w-0 flex-1">
                    <dl>
                      <dt className="text-sm font-medium text-gray-500 truncate">
                        {stat.name}
                      </dt>
                      <dd className="flex items-baseline">
                        <div className="text-2xl font-semibold text-gray-900">
                          {stat.value}
                        </div>
                        <div className={`ml-2 flex items-baseline text-sm font-semibold ${
                          stat.changeType === 'positive' ? 'text-green-600' : 
                          stat.changeType === 'negative' ? 'text-red-600' : 'text-gray-500'
                        }`}>
                          {stat.change}
                        </div>
                      </dd>
                    </dl>
                  </div>
                </div>
              </div>
            );
          })}
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
                  placeholder="Search students by name, ID, email, major..."
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
                Export CSV
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
              <h3 className="text-sm font-medium text-gray-900 flex items-center gap-2">
                <Settings className="h-4 w-4" />
                Column Visibility
              </h3>
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
            <div className="grid grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4">
              {table.getAllColumns().map((column) => {
                if (!column.columnDef.header) return null;
                return (
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
                );
              })}
            </div>
          </div>
        </div>

        {/* Table */}
        <div className="bg-white rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200">
            <h3 className="text-lg font-medium text-gray-900">
              Student Database Table
            </h3>
            <p className="mt-1 text-sm text-gray-600">
              Drag column headers to reorder • Click headers to sort • Use search to filter across all fields
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
                  {table.getRowModel().rows.map((row, index) => (
                    <tr key={row.id} className={`hover:bg-gray-50 ${index % 2 === 0 ? 'bg-white' : 'bg-gray-25'}`}>
                      {row.getVisibleCells().map((cell) => (
                        <td key={cell.id} className="px-4 py-3 whitespace-nowrap text-sm">
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
                  <span className="font-medium">{table.getFilteredRowModel().rows.length}</span> students
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

        {/* Features Info */}
        <div className="mt-8 bg-gradient-to-br from-blue-600 via-purple-600 to-indigo-700 rounded-lg p-8 text-white">
          <h3 className="text-xl font-bold mb-6">✨ Student Information System Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <GripVertical className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Drag & Drop Columns</h4>
                <p className="text-blue-100 text-sm">Reorder table columns by dragging headers to customize your view</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <UserCheck className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Student Status Tracking</h4>
                <p className="text-blue-100 text-sm">Monitor active, graduated, suspended, and other student statuses</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Search className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Global Search</h4>
                <p className="text-blue-100 text-sm">Search across names, IDs, emails, majors, and all student fields</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Eye className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Column Visibility</h4>
                <p className="text-blue-100 text-sm">Show/hide columns including legacy data, UUIDs, and timestamps</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <GraduationCap className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Academic Information</h4>
                <p className="text-blue-100 text-sm">View majors, GPA, credits, and academic progression data</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Settings className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Multi-Column Sorting</h4>
                <p className="text-blue-100 text-sm">Sort by multiple columns simultaneously for complex data analysis</p>
              </div>
            </div>
          </div>
          
          <div className="mt-8 p-4 bg-white/10 rounded-lg">
            <h4 className="font-semibold mb-2">🎯 Real Student Data Fields</h4>
            <p className="text-blue-100 text-sm">
              This demo uses your actual StudentProfile and Person model structure from <code>apps/people</code>, 
              including all fields like student_id, khmer_name, monk status, transfer status, study time preferences, 
              major declarations, and comprehensive demographic information.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentInformationTable;