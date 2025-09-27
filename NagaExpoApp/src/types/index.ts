export interface User {
  id: string;
  name: string;
  email: string;
  role: 'student' | 'teacher' | 'admin';
}

export interface AuthStore {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface AttendanceRecord {
  id: number;
  course: string;
  date: string;
  status: 'present' | 'absent' | 'late';
}

export interface Grade {
  id: number;
  course: string;
  grade: string;
  points: number;
}

export interface ApiResponse<T = any> {
  data: T;
  message?: string;
  success: boolean;
}