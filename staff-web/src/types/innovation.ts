/**
 * Innovation Module Types
 *
 * Core type definitions for AI-powered features and advanced analytics
 */

// AI/ML Model Types
export interface AIModel {
  id: string;
  name: string;
  version: string;
  type: 'classification' | 'regression' | 'clustering' | 'nlp' | 'computer_vision';
  status: 'training' | 'ready' | 'error' | 'updating';
  accuracy?: number;
  lastTrained: Date;
  confidence?: number;
}

export interface PredictionResult {
  id: string;
  modelId: string;
  result: any;
  confidence: number;
  timestamp: Date;
  explanation?: string;
  factors?: Array<{
    factor: string;
    impact: number;
    positive: boolean;
  }>;
}

// Student Success Prediction Types
export interface StudentRiskFactor {
  category: 'academic' | 'attendance' | 'financial' | 'behavioral' | 'social';
  factor: string;
  impact: number; // -1 to 1
  confidence: number; // 0 to 1
  description: string;
  recommendation?: string;
}

export interface StudentSuccessPrediction {
  studentId: string;
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  graduationProbability: number;
  nextTermGPA: number;
  riskFactors: StudentRiskFactor[];
  interventions: Intervention[];
  lastUpdated: Date;
}

export interface Intervention {
  id: string;
  type: 'academic_support' | 'financial_aid' | 'counseling' | 'tutoring' | 'mentoring';
  title: string;
  description: string;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  estimatedImpact: number;
  timeToImplement: string;
  cost?: number;
  assignedTo?: string;
  status: 'recommended' | 'active' | 'completed' | 'declined';
  successRate?: number;
}

// Communication Types
export interface Message {
  id: string;
  senderId: string;
  recipientIds: string[];
  subject?: string;
  content: string;
  type: 'direct' | 'announcement' | 'emergency' | 'system';
  priority: 'low' | 'normal' | 'high' | 'urgent';
  timestamp: Date;
  readBy: Array<{
    userId: string;
    readAt: Date;
  }>;
  attachments?: FileAttachment[];
  parentMessageId?: string;
  tags?: string[];
}

export interface CommunicationChannel {
  id: string;
  name: string;
  type: 'public' | 'private' | 'department' | 'class' | 'project';
  description: string;
  memberIds: string[];
  admins: string[];
  settings: {
    allowFiles: boolean;
    allowVideoCalls: boolean;
    autoTranslate: boolean;
    retentionDays?: number;
  };
  createdAt: Date;
}

// Document Intelligence Types
export interface ProcessedDocument {
  id: string;
  originalName: string;
  processedAt: Date;
  type: 'student_record' | 'transcript' | 'financial' | 'enrollment' | 'administrative';
  extractedText: string;
  confidence: number;
  entities: DocumentEntity[];
  classification: string;
  metadata: Record<string, any>;
  verificationStatus: 'pending' | 'verified' | 'rejected';
}

export interface DocumentEntity {
  type: 'person' | 'date' | 'grade' | 'course' | 'amount' | 'institution';
  value: string;
  confidence: number;
  position: {
    page: number;
    x: number;
    y: number;
    width: number;
    height: number;
  };
}

// Workflow Automation Types
export interface WorkflowNode {
  id: string;
  type: 'trigger' | 'condition' | 'action' | 'approval' | 'notification';
  label: string;
  config: Record<string, any>;
  position: { x: number; y: number };
  inputs?: string[];
  outputs?: string[];
}

export interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
  label?: string;
}

export interface Workflow {
  id: string;
  name: string;
  description: string;
  category: 'enrollment' | 'grading' | 'communication' | 'finance' | 'administrative';
  status: 'draft' | 'active' | 'paused' | 'archived';
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  triggers: string[];
  createdBy: string;
  createdAt: Date;
  lastModified: Date;
  executionCount: number;
  successRate: number;
}

// Analytics Types
export interface AnalyticsQuery {
  id: string;
  name: string;
  description: string;
  query: string;
  type: 'sql' | 'nosql' | 'graphql';
  parameters: QueryParameter[];
  visualizations: VisualizationConfig[];
  schedule?: ScheduleConfig;
  createdBy: string;
  createdAt: Date;
}

export interface QueryParameter {
  name: string;
  type: 'string' | 'number' | 'date' | 'boolean' | 'array';
  required: boolean;
  defaultValue?: any;
  options?: any[];
}

export interface VisualizationConfig {
  type: 'chart' | 'table' | 'map' | 'gauge' | 'metric';
  chartType?: 'line' | 'bar' | 'pie' | 'scatter' | 'area' | 'heatmap';
  config: Record<string, any>;
  title: string;
  description?: string;
}

export interface ScheduleConfig {
  frequency: 'once' | 'daily' | 'weekly' | 'monthly' | 'quarterly';
  time?: string;
  dayOfWeek?: number;
  dayOfMonth?: number;
  timezone?: string;
  recipients?: string[];
}

// Resource Optimization Types
export interface ResourceUtilization {
  resourceId: string;
  resourceType: 'classroom' | 'equipment' | 'staff' | 'facility';
  utilizationRate: number;
  capacity: number;
  currentUsage: number;
  peakUsage: number;
  trends: Array<{
    period: string;
    utilization: number;
  }>;
  optimization?: {
    recommendation: string;
    potentialImprovement: number;
    implementationCost?: number;
  };
}

export interface FacilityMetrics {
  facilityId: string;
  name: string;
  type: 'classroom' | 'lab' | 'office' | 'common_area' | 'outdoor';
  sensors: Array<{
    type: 'temperature' | 'humidity' | 'occupancy' | 'air_quality' | 'energy';
    value: number;
    unit: string;
    timestamp: Date;
    status: 'normal' | 'warning' | 'critical';
  }>;
  maintenance: {
    lastService: Date;
    nextService: Date;
    issues: number;
    priority: 'low' | 'medium' | 'high';
  };
}

// Mobile & Accessibility Types
export interface AccessibilityAudit {
  pageUrl: string;
  timestamp: Date;
  wcagLevel: 'A' | 'AA' | 'AAA';
  score: number;
  issues: Array<{
    severity: 'low' | 'medium' | 'high' | 'critical';
    principle: 'perceivable' | 'operable' | 'understandable' | 'robust';
    guideline: string;
    description: string;
    element?: string;
    suggestion: string;
  }>;
  improvements: string[];
}

export interface PWAMetrics {
  installPrompts: number;
  installations: number;
  offlineUsage: number;
  performance: {
    loadTime: number;
    firstContentfulPaint: number;
    largestContentfulPaint: number;
    interactionToNextPaint: number;
  };
  engagement: {
    dailyActiveUsers: number;
    sessionDuration: number;
    bounceRate: number;
  };
}

// File and Media Types
export interface FileAttachment {
  id: string;
  name: string;
  size: number;
  type: string;
  url: string;
  thumbnail?: string;
  uploadedBy: string;
  uploadedAt: Date;
  scanned?: boolean;
  scanResults?: {
    safe: boolean;
    threats?: string[];
  };
}

// Common utility types
export interface ApiResponse<T> {
  data: T;
  success: boolean;
  message?: string;
  errors?: string[];
  meta?: {
    total?: number;
    page?: number;
    limit?: number;
  };
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  limit: number;
  hasMore: boolean;
}

export interface FilterConfig {
  field: string;
  operator: 'eq' | 'ne' | 'gt' | 'gte' | 'lt' | 'lte' | 'in' | 'like' | 'between';
  value: any;
  label?: string;
}

export interface SortConfig {
  field: string;
  direction: 'asc' | 'desc';
  label?: string;
}