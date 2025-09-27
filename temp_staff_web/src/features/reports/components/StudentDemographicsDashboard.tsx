import React, { useState, useMemo } from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  PieChart,
  Pie,
  Cell,
  LineChart,
  Line,
  AreaChart,
  Area,
  ResponsiveContainer,
  ScatterChart,
  Scatter,
} from 'recharts';
import {
  Users,
  MapPin,
  GraduationCap,
  Calendar,
  Phone,
  Mail,
  Clock,
  TrendingUp,
  Filter,
  ArrowLeft,
  Eye,
  UserCheck,
  AlertCircle,
  BookOpen,
  Target,
  Globe,
  Home,
  School,
  Heart,
  Star,
  Zap,
} from 'lucide-react';

// Enhanced Student Data Interface with Related Information
interface StudentData {
  id: string;
  person_id: number;
  student_id: number;
  formatted_student_id: string;
  full_name: string;
  khmer_name: string;
  preferred_gender: 'M' | 'F' | 'N' | 'X';
  age: number;
  date_of_birth: string;
  birth_province: string;
  citizenship: string;
  current_status: 'ACTIVE' | 'INACTIVE' | 'GRADUATED' | 'DROPPED' | 'SUSPENDED' | 'TRANSFERRED' | 'FROZEN' | 'UNKNOWN';
  is_monk: boolean;
  is_transfer_student: boolean;
  study_time_preference: 'morning' | 'afternoon' | 'evening';
  school_email?: string;
  current_gpa?: number;
  total_credits?: number;
  declared_major_name?: string;
  enrollment_year?: number;
  
  // Related data
  emergency_contacts: EmergencyContact[];
  enrollments: Enrollment[];
  phone_numbers: PhoneNumber[];
}

interface EmergencyContact {
  id: number;
  name: string;
  relationship: string;
  phone: string;
  is_primary: boolean;
}

interface Enrollment {
  id: number;
  course_name: string;
  term: string;
  status: string;
  grade?: string;
  credits: number;
}

interface PhoneNumber {
  id: number;
  number: string;
  type: string;
  is_primary: boolean;
}

// Comprehensive sample data with related information
const comprehensiveStudentData: StudentData[] = [
  {
    id: '1',
    person_id: 1001,
    student_id: 18001,
    formatted_student_id: '18001',
    full_name: 'CHEA SOKHA',
    khmer_name: 'ជា សុខា',
    preferred_gender: 'M',
    age: 23,
    date_of_birth: '2001-03-15',
    birth_province: 'Phnom Penh',
    citizenship: 'KH',
    current_status: 'ACTIVE',
    is_monk: false,
    is_transfer_student: false,
    study_time_preference: 'evening',
    school_email: 'chea.sokha@naga.edu.kh',
    current_gpa: 3.75,
    total_credits: 45,
    declared_major_name: 'Computer Science',
    enrollment_year: 2022,
    emergency_contacts: [
      { id: 1, name: 'Chea Sophea', relationship: 'Father', phone: '+855123456789', is_primary: true },
      { id: 2, name: 'Lim Bopha', relationship: 'Mother', phone: '+855987654321', is_primary: false },
    ],
    enrollments: [
      { id: 1, course_name: 'Data Structures', term: '2024-Spring', status: 'Enrolled', credits: 3 },
      { id: 2, course_name: 'Web Development', term: '2024-Spring', status: 'Enrolled', credits: 3 },
    ],
    phone_numbers: [
      { id: 1, number: '+855111222333', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '2',
    person_id: 1002,
    student_id: 18002,
    formatted_student_id: '18002',
    full_name: 'LIM SREYPICH',
    khmer_name: 'លឹម ស្រីពេជ្រ',
    preferred_gender: 'F',
    age: 24,
    date_of_birth: '2000-07-22',
    birth_province: 'Siem Reap',
    citizenship: 'KH',
    current_status: 'ACTIVE',
    is_monk: false,
    is_transfer_student: true,
    study_time_preference: 'morning',
    school_email: 'lim.sreypich@naga.edu.kh',
    current_gpa: 3.92,
    total_credits: 78,
    declared_major_name: 'Business Administration',
    enrollment_year: 2021,
    emergency_contacts: [
      { id: 3, name: 'Lim Dara', relationship: 'Father', phone: '+855444555666', is_primary: true },
    ],
    enrollments: [
      { id: 3, course_name: 'Business Strategy', term: '2024-Spring', status: 'Enrolled', credits: 4 },
      { id: 4, course_name: 'Marketing', term: '2024-Spring', status: 'Completed', grade: 'A', credits: 3 },
    ],
    phone_numbers: [
      { id: 2, number: '+855222333444', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '3',
    person_id: 1003,
    student_id: 17845,
    formatted_student_id: '17845',
    full_name: 'PREAH VICHEKA',
    khmer_name: 'ព្រះ វិជេកា',
    preferred_gender: 'M',
    age: 25,
    date_of_birth: '1999-11-08',
    birth_province: 'Battambang',
    citizenship: 'KH',
    current_status: 'ACTIVE',
    is_monk: true,
    is_transfer_student: false,
    study_time_preference: 'afternoon',
    school_email: 'preah.vicheka@naga.edu.kh',
    current_gpa: 4.0,
    total_credits: 92,
    declared_major_name: 'Buddhist Studies',
    enrollment_year: 2020,
    emergency_contacts: [
      { id: 4, name: 'Wat Preah Ang', relationship: 'Temple', phone: '+855555666777', is_primary: true },
    ],
    enrollments: [
      { id: 5, course_name: 'Buddhist Philosophy', term: '2024-Spring', status: 'Enrolled', credits: 4 },
      { id: 6, course_name: 'Meditation Studies', term: '2024-Spring', status: 'Enrolled', credits: 2 },
    ],
    phone_numbers: [
      { id: 3, number: '+855333444555', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '4',
    person_id: 1004,
    student_id: 18125,
    formatted_student_id: '18125',
    full_name: 'NGUYEN THI LINH',
    khmer_name: '',
    preferred_gender: 'F',
    age: 22,
    date_of_birth: '2002-01-30',
    birth_province: 'International',
    citizenship: 'VN',
    current_status: 'ACTIVE',
    is_monk: false,
    is_transfer_student: true,
    study_time_preference: 'evening',
    school_email: 'nguyen.linh@naga.edu.kh',
    current_gpa: 3.85,
    total_credits: 32,
    declared_major_name: 'International Relations',
    enrollment_year: 2023,
    emergency_contacts: [
      { id: 5, name: 'Nguyen Van Duc', relationship: 'Father', phone: '+84987654321', is_primary: true },
      { id: 6, name: 'Tran Thi Mai', relationship: 'Mother', phone: '+84123456789', is_primary: false },
    ],
    enrollments: [
      { id: 7, course_name: 'International Law', term: '2024-Spring', status: 'Enrolled', credits: 3 },
      { id: 8, course_name: 'Global Economics', term: '2024-Spring', status: 'Enrolled', credits: 3 },
    ],
    phone_numbers: [
      { id: 4, number: '+84444555666', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '5',
    person_id: 1005,
    student_id: 18089,
    formatted_student_id: '18089',
    full_name: 'KONG PISACH',
    khmer_name: 'គង ពិសាច',
    preferred_gender: 'M',
    age: 22,
    date_of_birth: '2001-12-05',
    birth_province: 'Kandal',
    citizenship: 'KH',
    current_status: 'SUSPENDED',
    is_monk: false,
    is_transfer_student: false,
    study_time_preference: 'morning',
    school_email: 'kong.pisach@naga.edu.kh',
    current_gpa: 2.45,
    total_credits: 68,
    declared_major_name: 'Mechanical Engineering',
    enrollment_year: 2022,
    emergency_contacts: [
      { id: 7, name: 'Kong Rithy', relationship: 'Brother', phone: '+855666777888', is_primary: true },
    ],
    enrollments: [
      { id: 9, course_name: 'Engineering Math', term: '2023-Fall', status: 'Failed', grade: 'F', credits: 4 },
      { id: 10, course_name: 'Physics', term: '2023-Fall', status: 'Incomplete', credits: 3 },
    ],
    phone_numbers: [
      { id: 5, number: '+855777888999', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '6',
    person_id: 1006,
    student_id: 17234,
    formatted_student_id: '17234',
    full_name: 'SOM CHANMONY',
    khmer_name: 'សុំ ច័ន្ទមុនី',
    preferred_gender: 'F',
    age: 26,
    date_of_birth: '1998-06-18',
    birth_province: 'Takeo',
    citizenship: 'KH',
    current_status: 'GRADUATED',
    is_monk: false,
    is_transfer_student: false,
    study_time_preference: 'evening',
    school_email: 'som.chanmony@naga.edu.kh',
    current_gpa: 3.68,
    total_credits: 120,
    declared_major_name: 'English Literature',
    enrollment_year: 2019,
    emergency_contacts: [
      { id: 8, name: 'Som Virak', relationship: 'Husband', phone: '+855888999000', is_primary: true },
    ],
    enrollments: [
      { id: 11, course_name: 'English Literature', term: '2023-Fall', status: 'Completed', grade: 'A', credits: 3 },
      { id: 12, course_name: 'Creative Writing', term: '2023-Fall', status: 'Completed', grade: 'A-', credits: 3 },
    ],
    phone_numbers: [
      { id: 6, number: '+855999000111', type: 'mobile', is_primary: true },
    ],
  },
  // Adding more diverse demographic data
  {
    id: '7',
    person_id: 1007,
    student_id: 18156,
    formatted_student_id: '18156',
    full_name: 'PICH SOKHA',
    khmer_name: 'ពេជ្រ សុខា',
    preferred_gender: 'F',
    age: 19,
    date_of_birth: '2004-09-12',
    birth_province: 'Kampong Cham',
    citizenship: 'KH',
    current_status: 'ACTIVE',
    is_monk: false,
    is_transfer_student: false,
    study_time_preference: 'morning',
    school_email: 'pich.sokha@naga.edu.kh',
    current_gpa: 3.2,
    total_credits: 15,
    declared_major_name: 'Psychology',
    enrollment_year: 2024,
    emergency_contacts: [
      { id: 9, name: 'Pich Davith', relationship: 'Father', phone: '+855111222333', is_primary: true },
    ],
    enrollments: [
      { id: 13, course_name: 'Intro to Psychology', term: '2024-Spring', status: 'Enrolled', credits: 3 },
    ],
    phone_numbers: [
      { id: 7, number: '+855222444666', type: 'mobile', is_primary: true },
    ],
  },
  {
    id: '8',
    person_id: 1008,
    student_id: 17456,
    formatted_student_id: '17456',
    full_name: 'JAMES SMITH',
    khmer_name: '',
    preferred_gender: 'M',
    age: 28,
    date_of_birth: '1995-04-03',
    birth_province: 'International',
    citizenship: 'US',
    current_status: 'ACTIVE',
    is_monk: false,
    is_transfer_student: true,
    study_time_preference: 'afternoon',
    school_email: 'james.smith@naga.edu.kh',
    current_gpa: 3.5,
    total_credits: 95,
    declared_major_name: 'English Teaching',
    enrollment_year: 2020,
    emergency_contacts: [
      { id: 10, name: 'Robert Smith', relationship: 'Father', phone: '+1555123456', is_primary: true },
    ],
    enrollments: [
      { id: 14, course_name: 'Teaching Methodology', term: '2024-Spring', status: 'Enrolled', credits: 4 },
    ],
    phone_numbers: [
      { id: 8, number: '+1555987654', type: 'mobile', is_primary: true },
    ],
  },
];

const COLORS = {
  primary: ['#3B82F6', '#6366F1', '#8B5CF6', '#A855F7'],
  secondary: ['#10B981', '#059669', '#047857', '#065F46'],
  accent: ['#F59E0B', '#D97706', '#B45309', '#92400E'],
  status: ['#EF4444', '#F97316', '#EAB308', '#84CC16', '#22C55E'],
};

const StudentDemographicsDashboard: React.FC = () => {
  const [selectedSegment, setSelectedSegment] = useState<string | null>(null);
  const [selectedStudents, setSelectedStudents] = useState<StudentData[]>([]);
  const [activeView, setActiveView] = useState<'overview' | 'students' | 'details'>('overview');
  const [selectedStudent, setSelectedStudent] = useState<StudentData | null>(null);

  // Calculate demographic insights
  const demographics = useMemo(() => {
    const data = comprehensiveStudentData;

    // Gender distribution
    const genderData = [
      { name: 'Male', value: data.filter(s => s.preferred_gender === 'M').length, students: data.filter(s => s.preferred_gender === 'M') },
      { name: 'Female', value: data.filter(s => s.preferred_gender === 'F').length, students: data.filter(s => s.preferred_gender === 'F') },
      { name: 'Other', value: data.filter(s => ['N', 'X'].includes(s.preferred_gender)).length, students: data.filter(s => ['N', 'X'].includes(s.preferred_gender)) },
    ];

    // Age distribution
    const ageGroups = [
      { name: '18-20', min: 18, max: 20 },
      { name: '21-23', min: 21, max: 23 },
      { name: '24-26', min: 24, max: 26 },
      { name: '27+', min: 27, max: 100 },
    ];
    const ageData = ageGroups.map(group => ({
      name: group.name,
      value: data.filter(s => s.age >= group.min && s.age <= group.max).length,
      students: data.filter(s => s.age >= group.min && s.age <= group.max),
    }));

    // Province distribution
    const provinceData = [...new Set(data.map(s => s.birth_province))]
      .map(province => ({
        name: province,
        value: data.filter(s => s.birth_province === province).length,
        students: data.filter(s => s.birth_province === province),
      }))
      .sort((a, b) => b.value - a.value);

    // Status distribution
    const statusData = [...new Set(data.map(s => s.current_status))]
      .map(status => ({
        name: status,
        value: data.filter(s => s.current_status === status).length,
        students: data.filter(s => s.current_status === status),
      }));

    // Major distribution
    const majorData = [...new Set(data.map(s => s.declared_major_name).filter(Boolean))]
      .map(major => ({
        name: major!,
        value: data.filter(s => s.declared_major_name === major).length,
        students: data.filter(s => s.declared_major_name === major),
      }))
      .sort((a, b) => b.value - a.value);

    // Study time preference
    const studyTimeData = [
      { name: 'Morning', value: data.filter(s => s.study_time_preference === 'morning').length, students: data.filter(s => s.study_time_preference === 'morning') },
      { name: 'Afternoon', value: data.filter(s => s.study_time_preference === 'afternoon').length, students: data.filter(s => s.study_time_preference === 'afternoon') },
      { name: 'Evening', value: data.filter(s => s.study_time_preference === 'evening').length, students: data.filter(s => s.study_time_preference === 'evening') },
    ];

    // Special categories
    const specialData = [
      { name: 'Monks', value: data.filter(s => s.is_monk).length, students: data.filter(s => s.is_monk) },
      { name: 'Transfer Students', value: data.filter(s => s.is_transfer_student).length, students: data.filter(s => s.is_transfer_student) },
      { name: 'International Students', value: data.filter(s => s.citizenship !== 'KH').length, students: data.filter(s => s.citizenship !== 'KH') },
    ];

    // GPA distribution
    const gpaRanges = [
      { name: '3.5+', min: 3.5, max: 4.0 },
      { name: '3.0-3.49', min: 3.0, max: 3.49 },
      { name: '2.5-2.99', min: 2.5, max: 2.99 },
      { name: '<2.5', min: 0, max: 2.49 },
    ];
    const gpaData = gpaRanges.map(range => ({
      name: range.name,
      value: data.filter(s => s.current_gpa && s.current_gpa >= range.min && s.current_gpa <= range.max).length,
      students: data.filter(s => s.current_gpa && s.current_gpa >= range.min && s.current_gpa <= range.max),
    }));

    return {
      gender: genderData,
      age: ageData,
      province: provinceData,
      status: statusData,
      major: majorData,
      studyTime: studyTimeData,
      special: specialData,
      gpa: gpaData,
    };
  }, []);

  const handleSegmentClick = (segmentType: string, data: any) => {
    setSelectedSegment(`${segmentType}: ${data.name}`);
    setSelectedStudents(data.students);
    setActiveView('students');
  };

  const handleStudentClick = (student: StudentData) => {
    setSelectedStudent(student);
    setActiveView('details');
  };

  const renderOverview = () => (
    <div className="space-y-8">
      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        <div className="bg-gradient-to-r from-blue-500 to-blue-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-blue-100 text-sm">Total Students</p>
              <p className="text-2xl font-bold">{comprehensiveStudentData.length}</p>
            </div>
            <Users className="h-8 w-8 text-blue-200" />
          </div>
        </div>
        
        <div className="bg-gradient-to-r from-green-500 to-green-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-green-100 text-sm">Active Students</p>
              <p className="text-2xl font-bold">{demographics.status.find(s => s.name === 'ACTIVE')?.value || 0}</p>
            </div>
            <UserCheck className="h-8 w-8 text-green-200" />
          </div>
        </div>

        <div className="bg-gradient-to-r from-purple-500 to-purple-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-purple-100 text-sm">Avg GPA</p>
              <p className="text-2xl font-bold">
                {(comprehensiveStudentData.filter(s => s.current_gpa).reduce((sum, s) => sum + (s.current_gpa || 0), 0) / 
                  comprehensiveStudentData.filter(s => s.current_gpa).length).toFixed(2)}
              </p>
            </div>
            <Star className="h-8 w-8 text-purple-200" />
          </div>
        </div>

        <div className="bg-gradient-to-r from-orange-500 to-orange-600 rounded-lg p-6 text-white">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-orange-100 text-sm">Majors Offered</p>
              <p className="text-2xl font-bold">{demographics.major.length}</p>
            </div>
            <BookOpen className="h-8 w-8 text-orange-200" />
          </div>
        </div>
      </div>

      {/* Charts Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Gender Distribution */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Users className="h-5 w-5 text-blue-600" />
            Gender Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={demographics.gender}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
                onClick={(data) => handleSegmentClick('Gender', data)}
                className="cursor-pointer"
              >
                {demographics.gender.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS.primary[index % COLORS.primary.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        {/* Age Distribution */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Calendar className="h-5 w-5 text-green-600" />
            Age Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={demographics.age}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar 
                dataKey="value" 
                fill="#10B981" 
                onClick={(data) => handleSegmentClick('Age', data)}
                className="cursor-pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Province Distribution */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <MapPin className="h-5 w-5 text-purple-600" />
            Birth Province Distribution
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <BarChart data={demographics.province.slice(0, 6)}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar 
                dataKey="value" 
                fill="#8B5CF6" 
                onClick={(data) => handleSegmentClick('Province', data)}
                className="cursor-pointer"
              />
            </BarChart>
          </ResponsiveContainer>
        </div>

        {/* Study Time Preference */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Clock className="h-5 w-5 text-orange-600" />
            Study Time Preferences
          </h3>
          <ResponsiveContainer width="100%" height={250}>
            <PieChart>
              <Pie
                data={demographics.studyTime}
                cx="50%"
                cy="50%"
                innerRadius={60}
                outerRadius={100}
                dataKey="value"
                onClick={(data) => handleSegmentClick('Study Time', data)}
                className="cursor-pointer"
              >
                {demographics.studyTime.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={COLORS.accent[index % COLORS.accent.length]} />
                ))}
              </Pie>
              <Tooltip />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Special Categories */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <Target className="h-5 w-5 text-indigo-600" />
          Special Categories
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {demographics.special.map((item, index) => (
            <div
              key={item.name}
              onClick={() => handleSegmentClick('Special', item)}
              className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <span className="text-sm font-medium text-gray-700">{item.name}</span>
                <span className="text-lg font-bold text-indigo-600">{item.value}</span>
              </div>
              <div className="mt-2 bg-gray-200 rounded-full h-2">
                <div
                  className="bg-indigo-600 h-2 rounded-full"
                  style={{ width: `${(item.value / comprehensiveStudentData.length) * 100}%` }}
                />
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Academic Performance */}
      <div className="bg-white rounded-lg shadow-lg p-6">
        <h3 className="text-lg font-semibold mb-4 flex items-center gap-2">
          <GraduationCap className="h-5 w-5 text-red-600" />
          GPA Distribution
        </h3>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={demographics.gpa}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="name" />
            <YAxis />
            <Tooltip />
            <Bar 
              dataKey="value" 
              fill="#EF4444" 
              onClick={(data) => handleSegmentClick('GPA', data)}
              className="cursor-pointer"
            />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );

  const renderStudentsList = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow-lg p-6">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-xl font-bold text-gray-900">{selectedSegment}</h3>
            <p className="text-gray-600">{selectedStudents.length} students found</p>
          </div>
          <button
            onClick={() => setActiveView('overview')}
            className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Overview
          </button>
        </div>

        <div className="grid gap-4">
          {selectedStudents.map((student) => (
            <div
              key={student.id}
              onClick={() => handleStudentClick(student)}
              className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <div className="w-12 h-12 bg-gray-200 rounded-full flex items-center justify-center">
                    <Users className="h-6 w-6 text-gray-500" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-gray-900">{student.full_name}</h4>
                    {student.khmer_name && (
                      <p className="text-sm text-gray-500">{student.khmer_name}</p>
                    )}
                    <div className="flex items-center gap-4 mt-1">
                      <span className="text-sm text-gray-600">ID: {student.formatted_student_id}</span>
                      <span className="text-sm text-gray-600">Age: {student.age}</span>
                      <span className="text-sm text-gray-600">Major: {student.declared_major_name}</span>
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    student.current_status === 'ACTIVE' ? 'bg-green-100 text-green-800' :
                    student.current_status === 'SUSPENDED' ? 'bg-yellow-100 text-yellow-800' :
                    student.current_status === 'GRADUATED' ? 'bg-blue-100 text-blue-800' :
                    'bg-gray-100 text-gray-800'
                  }`}>
                    {student.current_status}
                  </span>
                  {student.is_monk && (
                    <span className="px-2 py-1 bg-orange-100 text-orange-800 rounded-full text-xs font-medium">
                      Monk
                    </span>
                  )}
                  {student.is_transfer_student && (
                    <span className="px-2 py-1 bg-blue-100 text-blue-800 rounded-full text-xs font-medium">
                      Transfer
                    </span>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderStudentDetails = () => {
    if (!selectedStudent) return null;

    return (
      <div className="space-y-6">
        <div className="bg-white rounded-lg shadow-lg p-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center">
                <Users className="h-8 w-8 text-gray-500" />
              </div>
              <div>
                <h3 className="text-2xl font-bold text-gray-900">{selectedStudent.full_name}</h3>
                {selectedStudent.khmer_name && (
                  <p className="text-lg text-gray-600">{selectedStudent.khmer_name}</p>
                )}
                <p className="text-gray-500">Student ID: {selectedStudent.formatted_student_id}</p>
              </div>
            </div>
            <button
              onClick={() => setActiveView('students')}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 text-gray-700 rounded-lg hover:bg-gray-200"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to List
            </button>
          </div>

          {/* Basic Info */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Calendar className="h-5 w-5 text-blue-600" />
                <span className="font-medium text-gray-700">Age & Birth</span>
              </div>
              <p className="text-lg font-semibold">{selectedStudent.age} years old</p>
              <p className="text-sm text-gray-600">{selectedStudent.date_of_birth}</p>
              <p className="text-sm text-gray-600">{selectedStudent.birth_province}</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <GraduationCap className="h-5 w-5 text-purple-600" />
                <span className="font-medium text-gray-700">Academic</span>
              </div>
              <p className="text-lg font-semibold">{selectedStudent.declared_major_name}</p>
              <p className="text-sm text-gray-600">GPA: {selectedStudent.current_gpa || 'N/A'}</p>
              <p className="text-sm text-gray-600">{selectedStudent.total_credits} credits</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Clock className="h-5 w-5 text-orange-600" />
                <span className="font-medium text-gray-700">Study Schedule</span>
              </div>
              <p className="text-lg font-semibold capitalize">{selectedStudent.study_time_preference}</p>
              <p className="text-sm text-gray-600">Entry: {selectedStudent.enrollment_year}</p>
            </div>

            <div className="bg-gray-50 rounded-lg p-4">
              <div className="flex items-center gap-2 mb-2">
                <Mail className="h-5 w-5 text-green-600" />
                <span className="font-medium text-gray-700">Contact</span>
              </div>
              <p className="text-sm text-gray-800">{selectedStudent.school_email}</p>
              <p className="text-sm text-gray-600">{selectedStudent.citizenship} citizen</p>
            </div>
          </div>
        </div>

        {/* Emergency Contacts */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Heart className="h-5 w-5 text-red-600" />
            Emergency Contacts ({selectedStudent.emergency_contacts.length})
          </h4>
          <div className="grid gap-4">
            {selectedStudent.emergency_contacts.map((contact) => (
              <div key={contact.id} className="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-gray-900">{contact.name}</p>
                  <p className="text-sm text-gray-600">{contact.relationship}</p>
                </div>
                <div className="text-right">
                  <p className="font-medium text-gray-900">{contact.phone}</p>
                  {contact.is_primary && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Primary</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Current Enrollments */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <BookOpen className="h-5 w-5 text-indigo-600" />
            Current Enrollments ({selectedStudent.enrollments.length})
          </h4>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Course</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Term</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Grade</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Credits</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {selectedStudent.enrollments.map((enrollment) => (
                  <tr key={enrollment.id}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium text-gray-900">
                      {enrollment.course_name}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {enrollment.term}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap">
                      <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                        enrollment.status === 'Enrolled' ? 'bg-green-100 text-green-800' :
                        enrollment.status === 'Completed' ? 'bg-blue-100 text-blue-800' :
                        enrollment.status === 'Failed' ? 'bg-red-100 text-red-800' :
                        'bg-yellow-100 text-yellow-800'
                      }`}>
                        {enrollment.status}
                      </span>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {enrollment.grade || '-'}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900">
                      {enrollment.credits}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Phone Numbers */}
        <div className="bg-white rounded-lg shadow-lg p-6">
          <h4 className="text-lg font-semibold mb-4 flex items-center gap-2">
            <Phone className="h-5 w-5 text-blue-600" />
            Phone Numbers ({selectedStudent.phone_numbers.length})
          </h4>
          <div className="grid gap-2">
            {selectedStudent.phone_numbers.map((phone) => (
              <div key={phone.id} className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <span className="font-medium text-gray-900">{phone.number}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm text-gray-600 capitalize">{phone.type}</span>
                  {phone.is_primary && (
                    <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded-full">Primary</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  return (
    <div className="min-h-screen bg-gray-50 p-6">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            📊 Student Demographics Intelligence
          </h1>
          <p className="text-gray-600">
            Interactive demographic insights with smart drill-down to student details, contacts, and academic records
          </p>
        </div>

        {/* Navigation Breadcrumbs */}
        {activeView !== 'overview' && (
          <div className="mb-6">
            <nav className="flex" aria-label="Breadcrumb">
              <ol className="inline-flex items-center space-x-1 md:space-x-3">
                <li className="inline-flex items-center">
                  <button
                    onClick={() => setActiveView('overview')}
                    className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-blue-600"
                  >
                    📊 Demographics Overview
                  </button>
                </li>
                {activeView === 'students' && (
                  <li>
                    <div className="flex items-center">
                      <span className="mx-1 text-gray-400">/</span>
                      <span className="text-sm font-medium text-gray-500">{selectedSegment}</span>
                    </div>
                  </li>
                )}
                {activeView === 'details' && (
                  <>
                    <li>
                      <div className="flex items-center">
                        <span className="mx-1 text-gray-400">/</span>
                        <button
                          onClick={() => setActiveView('students')}
                          className="text-sm font-medium text-gray-700 hover:text-blue-600"
                        >
                          {selectedSegment}
                        </button>
                      </div>
                    </li>
                    <li>
                      <div className="flex items-center">
                        <span className="mx-1 text-gray-400">/</span>
                        <span className="text-sm font-medium text-gray-500">{selectedStudent?.full_name}</span>
                      </div>
                    </li>
                  </>
                )}
              </ol>
            </nav>
          </div>
        )}

        {/* Content */}
        {activeView === 'overview' && renderOverview()}
        {activeView === 'students' && renderStudentsList()}
        {activeView === 'details' && renderStudentDetails()}

        {/* Features Info */}
        <div className="mt-12 bg-gradient-to-br from-indigo-600 via-purple-600 to-pink-600 rounded-lg p-8 text-white">
          <h3 className="text-xl font-bold mb-6">🎯 Smart Drill-Down Features</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            <div className="flex items-start gap-3">
              <Zap className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Interactive Charts</h4>
                <p className="text-indigo-100 text-sm">Click any chart segment to drill down into specific student groups</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Eye className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Student Details</h4>
                <p className="text-indigo-100 text-sm">View comprehensive profiles with contacts, enrollments, and academic data</p>
              </div>
            </div>
            <div className="flex items-start gap-3">
              <Target className="h-6 w-6 mt-1 flex-shrink-0" />
              <div>
                <h4 className="font-semibold">Related Information</h4>
                <p className="text-indigo-100 text-sm">Access emergency contacts, phone numbers, and enrollment history</p>
              </div>
            </div>
          </div>
          
          <div className="mt-8 p-4 bg-white/10 rounded-lg">
            <h4 className="font-semibold mb-2">🔗 Linkable Data Structure</h4>
            <p className="text-indigo-100 text-sm">
              This demo shows how demographic insights connect to detailed student records including emergency contacts, 
              enrollment history, phone numbers, and academic performance - all accessible through intelligent drill-down navigation.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StudentDemographicsDashboard;