/**
 * Innovation Module Exports
 *
 * Centralized exports for all innovation features including:
 * - AI/ML models and services
 * - Advanced communication and collaboration
 * - Document intelligence and blockchain verification
 * - Revolutionary educational technology components
 */

// Main Innovation Components
export { default as StudentSuccessPredictor } from './StudentSuccess/StudentSuccessPredictor';
export { default as StudentInterventionHub } from './StudentSuccess/StudentInterventionHub';
export { default as CommunicationHub } from './Communications/CommunicationHub';
export { default as CollaborationWorkspace } from './Communications/CollaborationWorkspace';
export { default as DocumentIntelligenceCenter } from './Documents/DocumentIntelligenceCenter';

// Advanced AI/ML Models
export { default as StudentSuccessModel, StudentSuccessModelFactory } from './ml/models/studentSuccess';
export { default as RiskAssessmentModel } from './ml/models/riskAssessment';
export { default as CourseRecommendationEngine } from './ml/models/courseRecommendation';
export { default as PerformancePredictionModel } from './ml/models/performancePrediction';

// NLP and AI Services
export { default as SentimentAnalysisService } from './ai/nlp/sentimentAnalysis';
export { default as TranslationService } from './ai/nlp/translation';

// Blockchain Services
export { default as DocumentVerificationService } from './blockchain/documentVerification';

// Central API Service
export { default as InnovationApiService, getInnovationApi } from './services/innovationApi';
export type {
  InnovationConfig,
  PredictionRequest,
  CommunicationRequest,
  DocumentRequest,
  AnalyticsRequest,
  BatchProcessingRequest,
  RealTimeSubscription
} from './services/innovationApi';

// Types and Interfaces
export * from '../../types/innovation';

// Utility Functions
export * from '../../utils/ai/modelUtils';
export * from '../../utils/communication/socketManager';

// Innovation Components Directory
export const INNOVATION_COMPONENTS = {
  // Main Components
  StudentSuccessPredictor: './StudentSuccess/StudentSuccessPredictor',
  StudentInterventionHub: './StudentSuccess/StudentInterventionHub',
  CommunicationHub: './Communications/CommunicationHub',
  CollaborationWorkspace: './Communications/CollaborationWorkspace',
  DocumentIntelligenceCenter: './Documents/DocumentIntelligenceCenter',

  // ML Components
  PredictionChart: './components/PredictionChart',
  RiskIndicator: './components/RiskIndicator',
  InterventionCard: './components/InterventionCard',

  // Communication Components
  ChatInterface: './components/ChatInterface',
  VideoCall: './components/VideoCall',

  // Document Components
  DocumentViewer: './components/DocumentViewer',
  OCRProcessor: './components/OCRProcessor',

  // Collaboration Components
  CollaborativeEditor: './components/CollaborativeEditor'
};

// Model Configuration Presets
export const MODEL_PRESETS = {
  BASIC_STUDENT_SUCCESS: {
    architecture: 'simple' as const,
    hiddenLayers: [128, 64, 32],
    dropoutRate: 0.3,
    learningRate: 0.001,
    batchSize: 32,
    epochs: 100,
    validationSplit: 0.2,
    earlyStoppingPatience: 10
  },

  ADVANCED_STUDENT_SUCCESS: {
    architecture: 'deep' as const,
    hiddenLayers: [512, 256, 128, 64],
    dropoutRate: 0.4,
    learningRate: 0.0005,
    batchSize: 64,
    epochs: 200,
    validationSplit: 0.2,
    earlyStoppingPatience: 15
  },

  TRANSFORMER_STUDENT_SUCCESS: {
    architecture: 'transformer' as const,
    hiddenLayers: [256, 128],
    dropoutRate: 0.2,
    learningRate: 0.0001,
    batchSize: 128,
    epochs: 150,
    validationSplit: 0.2,
    earlyStoppingPatience: 20
  }
};

// Service Configuration
export const INNOVATION_CONFIG = {
  DEFAULT: {
    aiModels: {
      enableStudentSuccess: true,
      enableRiskAssessment: true,
      enableCourseRecommendation: true,
      enablePerformancePrediction: true,
      modelUpdateFrequency: 24
    },
    communication: {
      enableRealTimeTranslation: true,
      enableSentimentAnalysis: true,
      enableVideoConferencing: true,
      maxConcurrentConnections: 1000
    },
    blockchain: {
      enableDocumentVerification: true,
      enableSmartContracts: false,
      networkId: 'mainnet',
      gasLimit: 500000
    },
    analytics: {
      enablePredictiveAnalytics: true,
      enableRealTimeMonitoring: true,
      dataRetentionDays: 365
    }
  },

  MINIMAL: {
    aiModels: {
      enableStudentSuccess: true,
      enableRiskAssessment: false,
      enableCourseRecommendation: false,
      enablePerformancePrediction: false,
      modelUpdateFrequency: 48
    },
    communication: {
      enableRealTimeTranslation: false,
      enableSentimentAnalysis: true,
      enableVideoConferencing: false,
      maxConcurrentConnections: 100
    },
    blockchain: {
      enableDocumentVerification: false,
      enableSmartContracts: false,
      networkId: 'testnet',
      gasLimit: 100000
    },
    analytics: {
      enablePredictiveAnalytics: true,
      enableRealTimeMonitoring: false,
      dataRetentionDays: 90
    }
  },

  ENTERPRISE: {
    aiModels: {
      enableStudentSuccess: true,
      enableRiskAssessment: true,
      enableCourseRecommendation: true,
      enablePerformancePrediction: true,
      modelUpdateFrequency: 12
    },
    communication: {
      enableRealTimeTranslation: true,
      enableSentimentAnalysis: true,
      enableVideoConferencing: true,
      maxConcurrentConnections: 10000
    },
    blockchain: {
      enableDocumentVerification: true,
      enableSmartContracts: true,
      networkId: 'mainnet',
      gasLimit: 1000000
    },
    analytics: {
      enablePredictiveAnalytics: true,
      enableRealTimeMonitoring: true,
      dataRetentionDays: 2555 // 7 years
    }
  }
};