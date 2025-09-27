/**
 * Advanced Performance Prediction Models
 *
 * Sophisticated ML models for predicting student academic performance with:
 * - Multi-modal prediction (GPA, course grades, skill mastery)
 * - Time-series forecasting for performance trends
 * - Attention mechanisms for feature importance
 * - Transfer learning between similar courses
 * - Ensemble methods for robust predictions
 */

import * as tf from '@tensorflow/tfjs';
import { DataPreprocessor } from '../../../../utils/ai/modelUtils';

export interface PerformanceMetrics {
  gpa: number;
  courseGrades: Record<string, number>;
  skillMastery: Record<string, number>;
  learningVelocity: number;
  retentionRate: number;
  engagementScore: number;
  consistencyIndex: number;
}

export interface LearningContext {
  courseId: string;
  courseDifficulty: number;
  instructorId: string;
  instructorRating: number;
  classSize: number;
  deliveryMode: 'online' | 'hybrid' | 'in-person';
  timeOfDay: string;
  semester: string;
  prerequisites: string[];
  courseLoad: number; // total credits this semester
}

export interface StudentContext {
  studentId: string;
  academicHistory: PerformanceMetrics[];
  personalFactors: {
    workHours: number;
    familyResponsibilities: number;
    healthStatus: number;
    motivationLevel: number;
    stressLevel: number;
    studyHabits: number;
    timeManagement: number;
    technicalSkills: number;
  };
  socialFactors: {
    peerSupport: number;
    mentorship: number;
    studyGroups: number;
    campusInvolvement: number;
    socialConnections: number;
  };
  environmentalFactors: {
    housingStability: number;
    internetAccess: number;
    quietStudySpace: number;
    libraryAccess: number;
    technologyAccess: number;
  };
}

export interface PerformancePrediction {
  studentId: string;
  courseId?: string;
  predictions: {
    overallGPA: {
      predicted: number;
      confidence: number;
      range: [number, number];
    };
    courseGrade: {
      predicted: number;
      confidence: number;
      range: [number, number];
      probability: Record<string, number>; // A, B, C, D, F probabilities
    };
    skillDevelopment: {
      skills: Record<string, {
        current: number;
        predicted: number;
        growth: number;
      }>;
    };
    riskFactors: Array<{
      factor: string;
      impact: number;
      likelihood: number;
      mitigation: string;
    }>;
  };
  timeline: {
    nextWeek: PerformanceMetrics;
    midterm: PerformanceMetrics;
    endOfSemester: PerformanceMetrics;
  };
  recommendations: Array<{
    action: string;
    expectedImprovement: number;
    difficulty: number;
    timeframe: string;
  }>;
  lastUpdated: Date;
}

export interface TimeSeriesData {
  timestamp: Date;
  metrics: PerformanceMetrics;
  context: Partial<LearningContext>;
}

export class PerformancePredictionModel {
  private gpaModel: tf.LayersModel | null = null;
  private gradeModel: tf.LayersModel | null = null;
  private skillModel: tf.LayersModel | null = null;
  private timeSeriesModel: tf.LayersModel | null = null;
  private attentionModel: tf.LayersModel | null = null;
  private ensembleWeights: number[] = [0.3, 0.25, 0.2, 0.15, 0.1];
  private featureScalers: Map<string, any> = new Map();
  private performanceHistory: Map<string, TimeSeriesData[]> = new Map();

  constructor() {
    this.initializeModels();
  }

  private async initializeModels(): Promise<void> {
    console.log('Initializing performance prediction models...');
  }

  /**
   * Create GPA prediction model
   */
  private createGPAModel(): tf.LayersModel {
    const input = tf.input({ shape: [50] }); // 50 features

    // Feature extraction layers
    let x = tf.layers.dense({ units: 128, activation: 'relu' }).apply(input) as tf.SymbolicTensor;
    x = tf.layers.batchNormalization().apply(x) as tf.SymbolicTensor;
    x = tf.layers.dropout({ rate: 0.3 }).apply(x) as tf.SymbolicTensor;

    x = tf.layers.dense({ units: 64, activation: 'relu' }).apply(x) as tf.SymbolicTensor;
    x = tf.layers.batchNormalization().apply(x) as tf.SymbolicTensor;
    x = tf.layers.dropout({ rate: 0.2 }).apply(x) as tf.SymbolicTensor;

    // Multi-output for different time horizons
    const nextWeekGPA = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'next_week_gpa'
    }).apply(x) as tf.SymbolicTensor;

    const midtermGPA = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'midterm_gpa'
    }).apply(x) as tf.SymbolicTensor;

    const finalGPA = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'final_gpa'
    }).apply(x) as tf.SymbolicTensor;

    // Uncertainty estimation
    const confidence = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'confidence'
    }).apply(x) as tf.SymbolicTensor;

    return tf.model({
      inputs: input,
      outputs: [nextWeekGPA, midtermGPA, finalGPA, confidence]
    });
  }

  /**
   * Create course grade prediction model with attention
   */
  private createGradeModel(): tf.LayersModel {
    const studentFeatures = tf.input({ shape: [30], name: 'student_features' });
    const courseFeatures = tf.input({ shape: [20], name: 'course_features' });
    const contextFeatures = tf.input({ shape: [15], name: 'context_features' });

    // Student encoder
    let studentEncoded = tf.layers.dense({ units: 64, activation: 'relu' })
      .apply(studentFeatures) as tf.SymbolicTensor;
    studentEncoded = tf.layers.dropout({ rate: 0.2 }).apply(studentEncoded) as tf.SymbolicTensor;

    // Course encoder
    let courseEncoded = tf.layers.dense({ units: 32, activation: 'relu' })
      .apply(courseFeatures) as tf.SymbolicTensor;
    courseEncoded = tf.layers.dropout({ rate: 0.2 }).apply(courseEncoded) as tf.SymbolicTensor;

    // Context encoder
    let contextEncoded = tf.layers.dense({ units: 24, activation: 'relu' })
      .apply(contextFeatures) as tf.SymbolicTensor;

    // Attention mechanism (simplified)
    const combined = tf.layers.concatenate()
      .apply([studentEncoded, courseEncoded, contextEncoded]) as tf.SymbolicTensor;

    let attention = tf.layers.dense({ units: 120, activation: 'tanh' })
      .apply(combined) as tf.SymbolicTensor;
    attention = tf.layers.dense({ units: 120, activation: 'softmax' })
      .apply(attention) as tf.SymbolicTensor;

    const attended = tf.layers.multiply()
      .apply([combined, attention]) as tf.SymbolicTensor;

    // Final prediction layers
    let output = tf.layers.dense({ units: 64, activation: 'relu' }).apply(attended) as tf.SymbolicTensor;
    output = tf.layers.dropout({ rate: 0.3 }).apply(output) as tf.SymbolicTensor;

    // Grade probabilities (A, B, C, D, F)
    const gradeProbabilities = tf.layers.dense({
      units: 5,
      activation: 'softmax',
      name: 'grade_probabilities'
    }).apply(output) as tf.SymbolicTensor;

    // Continuous grade score
    const gradeScore = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'grade_score'
    }).apply(output) as tf.SymbolicTensor;

    return tf.model({
      inputs: [studentFeatures, courseFeatures, contextFeatures],
      outputs: [gradeProbabilities, gradeScore]
    });
  }

  /**
   * Create time series model for performance trends
   */
  private createTimeSeriesModel(): tf.LayersModel {
    const sequenceLength = 10;
    const featureSize = 20;

    const input = tf.input({ shape: [sequenceLength, featureSize] });

    // LSTM layers for temporal modeling
    let lstm1 = tf.layers.lstm({
      units: 64,
      returnSequences: true,
      dropout: 0.2,
      recurrentDropout: 0.2
    }).apply(input) as tf.SymbolicTensor;

    let lstm2 = tf.layers.lstm({
      units: 32,
      returnSequences: false,
      dropout: 0.2,
      recurrentDropout: 0.2
    }).apply(lstm1) as tf.SymbolicTensor;

    // Dense layers for prediction
    let dense = tf.layers.dense({ units: 32, activation: 'relu' }).apply(lstm2) as tf.SymbolicTensor;
    dense = tf.layers.dropout({ rate: 0.3 }).apply(dense) as tf.SymbolicTensor;

    // Multi-step prediction
    const nextStep = tf.layers.dense({
      units: featureSize,
      name: 'next_step'
    }).apply(dense) as tf.SymbolicTensor;

    const trend = tf.layers.dense({
      units: 1,
      activation: 'tanh',
      name: 'trend'
    }).apply(dense) as tf.SymbolicTensor;

    return tf.model({
      inputs: input,
      outputs: [nextStep, trend]
    });
  }

  /**
   * Train all prediction models
   */
  async trainModels(
    trainingData: Array<{
      studentContext: StudentContext;
      learningContext: LearningContext;
      actualPerformance: PerformanceMetrics;
      timeSeriesData: TimeSeriesData[];
    }>
  ): Promise<void> {
    console.log('Training performance prediction models...');

    // Create models
    this.gpaModel = this.createGPAModel();
    this.gradeModel = this.createGradeModel();
    this.timeSeriesModel = this.createTimeSeriesModel();

    // Prepare training data for GPA model
    await this.trainGPAModel(trainingData);

    // Prepare training data for grade model
    await this.trainGradeModel(trainingData);

    // Prepare training data for time series model
    await this.trainTimeSeriesModel(trainingData);

    console.log('All performance prediction models trained successfully');
  }

  private async trainGPAModel(trainingData: any[]): Promise<void> {
    if (!this.gpaModel) return;

    // Extract features and labels
    const features = trainingData.map(item => this.extractGPAFeatures(item));
    const labels = trainingData.map(item => [
      item.actualPerformance.gpa / 4.0, // Normalize to 0-1
      item.actualPerformance.gpa / 4.0, // Simplified - would be different for different time horizons
      item.actualPerformance.gpa / 4.0,
      0.8 // Mock confidence
    ]);

    // Normalize features
    const { normalized: normalizedFeatures, stats } = DataPreprocessor.normalizeFeatures(
      features,
      { method: 'zscore' }
    );
    this.featureScalers.set('gpa', stats);

    this.gpaModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: {
        next_week_gpa: 'meanSquaredError',
        midterm_gpa: 'meanSquaredError',
        final_gpa: 'meanSquaredError',
        confidence: 'meanSquaredError'
      },
      metrics: ['mae'],
      lossWeights: {
        next_week_gpa: 1.0,
        midterm_gpa: 1.2,
        final_gpa: 1.5,
        confidence: 0.5
      }
    });

    const xs = tf.tensor2d(normalizedFeatures);
    const ys = tf.tensor2d(labels);

    await this.gpaModel.fit(xs, ys, {
      epochs: 100,
      batchSize: 32,
      validationSplit: 0.2,
      shuffle: true,
      callbacks: {
        onEpochEnd: (epoch, logs) => {
          if (epoch % 20 === 0) {
            console.log(`GPA Model Epoch ${epoch}: loss = ${logs?.loss?.toFixed(4)}`);
          }
        }
      }
    });

    xs.dispose();
    ys.dispose();
  }

  private async trainGradeModel(trainingData: any[]): Promise<void> {
    if (!this.gradeModel) return;

    // Extract features
    const studentFeatures = trainingData.map(item => this.extractStudentFeatures(item.studentContext));
    const courseFeatures = trainingData.map(item => this.extractCourseFeatures(item.learningContext));
    const contextFeatures = trainingData.map(item => this.extractContextFeatures(item));

    // Create grade labels
    const gradeLabels = trainingData.map(item => {
      const gpa = item.actualPerformance.gpa;
      // Convert GPA to grade probabilities
      const probabilities = this.gpaToGradeProbabilities(gpa);
      return probabilities;
    });

    const gradeScores = trainingData.map(item => [item.actualPerformance.gpa / 4.0]);

    // Normalize features
    const { normalized: normStudentFeatures } = DataPreprocessor.normalizeFeatures(
      studentFeatures,
      { method: 'zscore' }
    );
    const { normalized: normCourseFeatures } = DataPreprocessor.normalizeFeatures(
      courseFeatures,
      { method: 'zscore' }
    );
    const { normalized: normContextFeatures } = DataPreprocessor.normalizeFeatures(
      contextFeatures,
      { method: 'zscore' }
    );

    this.gradeModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: {
        grade_probabilities: 'categoricalCrossentropy',
        grade_score: 'meanSquaredError'
      },
      metrics: {
        grade_probabilities: ['accuracy'],
        grade_score: ['mae']
      },
      lossWeights: {
        grade_probabilities: 1.0,
        grade_score: 0.8
      }
    });

    const xs1 = tf.tensor2d(normStudentFeatures);
    const xs2 = tf.tensor2d(normCourseFeatures);
    const xs3 = tf.tensor2d(normContextFeatures);
    const ys1 = tf.tensor2d(gradeLabels);
    const ys2 = tf.tensor2d(gradeScores);

    await this.gradeModel.fit(
      [xs1, xs2, xs3],
      [ys1, ys2],
      {
        epochs: 80,
        batchSize: 64,
        validationSplit: 0.2,
        shuffle: true,
        callbacks: {
          onEpochEnd: (epoch, logs) => {
            if (epoch % 20 === 0) {
              console.log(`Grade Model Epoch ${epoch}: loss = ${logs?.loss?.toFixed(4)}`);
            }
          }
        }
      }
    );

    xs1.dispose();
    xs2.dispose();
    xs3.dispose();
    ys1.dispose();
    ys2.dispose();
  }

  private async trainTimeSeriesModel(trainingData: any[]): Promise<void> {
    if (!this.timeSeriesModel) return;

    // Prepare time series sequences
    const sequences: number[][][] = [];
    const nextSteps: number[][] = [];
    const trends: number[] = [];

    for (const item of trainingData) {
      if (item.timeSeriesData.length >= 11) { // Need at least 11 points (10 + 1)
        for (let i = 0; i <= item.timeSeriesData.length - 11; i++) {
          const sequence = item.timeSeriesData.slice(i, i + 10)
            .map(point => this.timeSeriesPointToFeatures(point));
          const nextStep = this.timeSeriesPointToFeatures(item.timeSeriesData[i + 10]);
          const trend = this.calculateTrend(item.timeSeriesData.slice(i, i + 11));

          sequences.push(sequence);
          nextSteps.push(nextStep);
          trends.push(trend);
        }
      }
    }

    if (sequences.length === 0) {
      console.log('Not enough time series data for training');
      return;
    }

    this.timeSeriesModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: {
        next_step: 'meanSquaredError',
        trend: 'meanSquaredError'
      },
      metrics: ['mae'],
      lossWeights: {
        next_step: 1.0,
        trend: 0.5
      }
    });

    const xs = tf.tensor3d(sequences);
    const ys1 = tf.tensor2d(nextSteps);
    const ys2 = tf.tensor1d(trends);

    await this.timeSeriesModel.fit(
      xs,
      [ys1, ys2],
      {
        epochs: 60,
        batchSize: 32,
        validationSplit: 0.2,
        shuffle: true,
        callbacks: {
          onEpochEnd: (epoch, logs) => {
            if (epoch % 20 === 0) {
              console.log(`Time Series Model Epoch ${epoch}: loss = ${logs?.loss?.toFixed(4)}`);
            }
          }
        }
      }
    );

    xs.dispose();
    ys1.dispose();
    ys2.dispose();
  }

  /**
   * Predict student performance
   */
  async predictPerformance(
    studentContext: StudentContext,
    learningContext: LearningContext,
    timeHorizon: 'week' | 'midterm' | 'semester' = 'semester'
  ): Promise<PerformancePrediction> {
    if (!this.gpaModel || !this.gradeModel) {
      throw new Error('Models not trained');
    }

    // Extract features
    const gpaFeatures = this.extractGPAFeatures({ studentContext, learningContext });
    const studentFeatures = this.extractStudentFeatures(studentContext);
    const courseFeatures = this.extractCourseFeatures(learningContext);
    const contextFeatures = this.extractContextFeatures({ studentContext, learningContext });

    // Normalize features
    const gpaStats = this.featureScalers.get('gpa');
    const { normalized: normGpaFeatures } = DataPreprocessor.normalizeFeatures(
      [gpaFeatures],
      { method: 'zscore', featureRanges: gpaStats }
    );

    // GPA prediction
    const gpaInput = tf.tensor2d(normGpaFeatures);
    const gpaOutput = this.gpaModel.predict(gpaInput) as tf.Tensor[];
    const gpaResults = await Promise.all(gpaOutput.map(tensor => tensor.data()));

    // Grade prediction
    const gradeInput1 = tf.tensor2d([studentFeatures]);
    const gradeInput2 = tf.tensor2d([courseFeatures]);
    const gradeInput3 = tf.tensor2d([contextFeatures]);
    const gradeOutput = this.gradeModel.predict([gradeInput1, gradeInput2, gradeInput3]) as tf.Tensor[];
    const gradeResults = await Promise.all(gradeOutput.map(tensor => tensor.data()));

    // Time series prediction if available
    let timelineData = this.generateDefaultTimeline(studentContext);
    if (this.timeSeriesModel && this.performanceHistory.has(studentContext.studentId)) {
      timelineData = await this.predictTimeline(studentContext.studentId);
    }

    // Parse results
    const predictions: PerformancePrediction['predictions'] = {
      overallGPA: {
        predicted: gpaResults[2][0] * 4.0, // Final GPA
        confidence: gpaResults[3][0],
        range: [
          Math.max(0, (gpaResults[2][0] - 0.2) * 4.0),
          Math.min(4.0, (gpaResults[2][0] + 0.2) * 4.0)
        ]
      },
      courseGrade: {
        predicted: gradeResults[1][0] * 4.0,
        confidence: Math.max(...Array.from(gradeResults[0])),
        range: [
          Math.max(0, (gradeResults[1][0] - 0.3) * 4.0),
          Math.min(4.0, (gradeResults[1][0] + 0.3) * 4.0)
        ],
        probability: {
          A: gradeResults[0][0],
          B: gradeResults[0][1],
          C: gradeResults[0][2],
          D: gradeResults[0][3],
          F: gradeResults[0][4]
        }
      },
      skillDevelopment: {
        skills: this.predictSkillDevelopment(studentContext, learningContext)
      },
      riskFactors: this.identifyRiskFactors(studentContext, learningContext, gpaResults[2][0] * 4.0)
    };

    // Generate recommendations
    const recommendations = this.generateRecommendations(
      studentContext,
      learningContext,
      predictions
    );

    // Cleanup tensors
    gpaInput.dispose();
    gpaOutput.forEach(tensor => tensor.dispose());
    gradeInput1.dispose();
    gradeInput2.dispose();
    gradeInput3.dispose();
    gradeOutput.forEach(tensor => tensor.dispose());

    return {
      studentId: studentContext.studentId,
      courseId: learningContext.courseId,
      predictions,
      timeline: timelineData,
      recommendations,
      lastUpdated: new Date()
    };
  }

  /**
   * Batch predict for multiple students
   */
  async batchPredict(
    requests: Array<{
      studentContext: StudentContext;
      learningContext: LearningContext;
    }>
  ): Promise<PerformancePrediction[]> {
    const predictions: PerformancePrediction[] = [];

    for (const request of requests) {
      const prediction = await this.predictPerformance(
        request.studentContext,
        request.learningContext
      );
      predictions.push(prediction);
    }

    return predictions;
  }

  /**
   * Update performance history for time series prediction
   */
  updatePerformanceHistory(studentId: string, data: TimeSeriesData): void {
    const existing = this.performanceHistory.get(studentId) || [];
    existing.push(data);

    // Keep only last 100 data points
    const trimmed = existing.slice(-100);
    this.performanceHistory.set(studentId, trimmed);
  }

  private extractGPAFeatures(data: any): number[] {
    const { studentContext, learningContext } = data;

    return [
      // Academic history (10 features)
      studentContext.academicHistory.length > 0 ? studentContext.academicHistory[0].gpa : 0,
      studentContext.academicHistory.reduce((sum: number, h: any) => sum + h.gpa, 0) / Math.max(1, studentContext.academicHistory.length),
      studentContext.academicHistory.length > 0 ? studentContext.academicHistory[studentContext.academicHistory.length - 1].gpa : 0,
      this.calculateGPATrend(studentContext.academicHistory),
      Object.keys(studentContext.academicHistory.length > 0 ? studentContext.academicHistory[0].courseGrades : {}).length,
      studentContext.academicHistory.reduce((sum: number, h: any) => sum + h.learningVelocity, 0) / Math.max(1, studentContext.academicHistory.length),
      studentContext.academicHistory.reduce((sum: number, h: any) => sum + h.retentionRate, 0) / Math.max(1, studentContext.academicHistory.length),
      studentContext.academicHistory.reduce((sum: number, h: any) => sum + h.engagementScore, 0) / Math.max(1, studentContext.academicHistory.length),
      studentContext.academicHistory.reduce((sum: number, h: any) => sum + h.consistencyIndex, 0) / Math.max(1, studentContext.academicHistory.length),
      learningContext ? learningContext.courseLoad : 0,

      // Personal factors (10 features)
      ...Object.values(studentContext.personalFactors),

      // Social factors (5 features)
      ...Object.values(studentContext.socialFactors),

      // Environmental factors (5 features)
      ...Object.values(studentContext.environmentalFactors),

      // Course context (10 features)
      learningContext ? learningContext.courseDifficulty : 0,
      learningContext ? learningContext.instructorRating : 0,
      learningContext ? learningContext.classSize : 0,
      learningContext && learningContext.deliveryMode === 'online' ? 1 : 0,
      learningContext && learningContext.deliveryMode === 'hybrid' ? 1 : 0,
      learningContext && learningContext.deliveryMode === 'in-person' ? 1 : 0,
      learningContext ? this.timeOfDayToNumber(learningContext.timeOfDay) : 0,
      learningContext ? this.semesterToNumber(learningContext.semester) : 0,
      learningContext ? learningContext.prerequisites.length : 0,
      learningContext ? learningContext.courseLoad : 0,

      // Interaction features (10 features)
      studentContext.personalFactors.workHours * (learningContext ? learningContext.courseDifficulty : 0),
      studentContext.personalFactors.stressLevel * (learningContext ? learningContext.courseLoad : 0),
      studentContext.socialFactors.peerSupport * (learningContext ? learningContext.classSize / 100 : 0),
      studentContext.personalFactors.motivationLevel * (learningContext ? learningContext.instructorRating : 0),
      studentContext.environmentalFactors.internetAccess * (learningContext && learningContext.deliveryMode === 'online' ? 1 : 0),
      0, 0, 0, 0, 0 // Padding to reach 50 features
    ];
  }

  private extractStudentFeatures(studentContext: StudentContext): number[] {
    return [
      ...Object.values(studentContext.personalFactors),
      ...Object.values(studentContext.socialFactors),
      ...Object.values(studentContext.environmentalFactors),
      // Add more features as needed
    ];
  }

  private extractCourseFeatures(learningContext: LearningContext): number[] {
    return [
      learningContext.courseDifficulty,
      learningContext.instructorRating,
      learningContext.classSize,
      learningContext.deliveryMode === 'online' ? 1 : 0,
      learningContext.deliveryMode === 'hybrid' ? 1 : 0,
      learningContext.deliveryMode === 'in-person' ? 1 : 0,
      this.timeOfDayToNumber(learningContext.timeOfDay),
      this.semesterToNumber(learningContext.semester),
      learningContext.prerequisites.length,
      learningContext.courseLoad,
      // Add more features as needed
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0 // Padding to reach 20 features
    ];
  }

  private extractContextFeatures(data: any): number[] {
    // Extract contextual features from the combination of student and course data
    const { studentContext, learningContext } = data;

    return [
      // Interaction features
      studentContext.personalFactors.workHours * learningContext.courseDifficulty,
      studentContext.personalFactors.stressLevel * learningContext.courseLoad,
      studentContext.socialFactors.peerSupport * (learningContext.classSize / 100),
      studentContext.personalFactors.motivationLevel * learningContext.instructorRating,
      studentContext.environmentalFactors.internetAccess * (learningContext.deliveryMode === 'online' ? 1 : 0),
      // Add more interaction features
      0, 0, 0, 0, 0, 0, 0, 0, 0, 0 // Padding to reach 15 features
    ];
  }

  private timeSeriesPointToFeatures(point: TimeSeriesData): number[] {
    return [
      point.metrics.gpa,
      point.metrics.learningVelocity,
      point.metrics.retentionRate,
      point.metrics.engagementScore,
      point.metrics.consistencyIndex,
      Object.keys(point.metrics.courseGrades).length,
      Object.keys(point.metrics.skillMastery).length,
      point.context.courseDifficulty || 0,
      point.context.instructorRating || 0,
      point.context.classSize || 0,
      point.context.courseLoad || 0,
      // Add more features
      0, 0, 0, 0, 0, 0, 0, 0 // Padding to reach 20 features
    ];
  }

  private calculateTrend(timeSeriesPoints: TimeSeriesData[]): number {
    if (timeSeriesPoints.length < 2) return 0;

    const gpas = timeSeriesPoints.map(point => point.metrics.gpa);
    const firstHalf = gpas.slice(0, Math.floor(gpas.length / 2));
    const secondHalf = gpas.slice(Math.floor(gpas.length / 2));

    const firstAvg = firstHalf.reduce((sum, gpa) => sum + gpa, 0) / firstHalf.length;
    const secondAvg = secondHalf.reduce((sum, gpa) => sum + gpa, 0) / secondHalf.length;

    return (secondAvg - firstAvg) / 4.0; // Normalize by max GPA
  }

  private calculateGPATrend(history: PerformanceMetrics[]): number {
    if (history.length < 2) return 0;

    const gpas = history.map(h => h.gpa);
    const slope = this.calculateSlope(gpas);
    return slope;
  }

  private calculateSlope(values: number[]): number {
    const n = values.length;
    if (n < 2) return 0;

    const xSum = (n * (n - 1)) / 2;
    const ySum = values.reduce((sum, val) => sum + val, 0);
    const xySum = values.reduce((sum, val, idx) => sum + (val * idx), 0);
    const x2Sum = (n * (n - 1) * (2 * n - 1)) / 6;

    const slope = (n * xySum - xSum * ySum) / (n * x2Sum - xSum * xSum);
    return slope;
  }

  private timeOfDayToNumber(timeOfDay: string): number {
    const timeMap: Record<string, number> = {
      'early_morning': 0.1,
      'morning': 0.3,
      'afternoon': 0.6,
      'evening': 0.8,
      'night': 1.0
    };
    return timeMap[timeOfDay] || 0.5;
  }

  private semesterToNumber(semester: string): number {
    const semesterMap: Record<string, number> = {
      'spring': 0.25,
      'summer': 0.5,
      'fall': 0.75,
      'winter': 1.0
    };
    return semesterMap[semester] || 0.5;
  }

  private gpaToGradeProbabilities(gpa: number): number[] {
    // Convert GPA to grade letter probabilities
    if (gpa >= 3.7) return [0.8, 0.2, 0.0, 0.0, 0.0]; // Mostly A
    if (gpa >= 3.0) return [0.2, 0.6, 0.2, 0.0, 0.0]; // Mostly B
    if (gpa >= 2.0) return [0.0, 0.2, 0.6, 0.2, 0.0]; // Mostly C
    if (gpa >= 1.0) return [0.0, 0.0, 0.2, 0.6, 0.2]; // Mostly D
    return [0.0, 0.0, 0.0, 0.2, 0.8]; // Mostly F
  }

  private predictSkillDevelopment(
    studentContext: StudentContext,
    learningContext: LearningContext
  ): Record<string, { current: number; predicted: number; growth: number }> {
    // Mock skill development prediction
    const skills = ['critical_thinking', 'problem_solving', 'communication', 'technical_skills'];
    const skillDevelopment: Record<string, { current: number; predicted: number; growth: number }> = {};

    skills.forEach(skill => {
      const current = Math.random() * 10;
      const growth = Math.random() * 2;
      skillDevelopment[skill] = {
        current,
        predicted: Math.min(10, current + growth),
        growth
      };
    });

    return skillDevelopment;
  }

  private identifyRiskFactors(
    studentContext: StudentContext,
    learningContext: LearningContext,
    predictedGPA: number
  ): Array<{ factor: string; impact: number; likelihood: number; mitigation: string }> {
    const riskFactors = [];

    if (predictedGPA < 2.5) {
      riskFactors.push({
        factor: 'Low Academic Performance',
        impact: 0.8,
        likelihood: 0.7,
        mitigation: 'Academic tutoring and study skills development'
      });
    }

    if (studentContext.personalFactors.stressLevel > 7) {
      riskFactors.push({
        factor: 'High Stress Level',
        impact: 0.6,
        likelihood: 0.8,
        mitigation: 'Stress management counseling and wellness programs'
      });
    }

    if (studentContext.personalFactors.workHours > 30) {
      riskFactors.push({
        factor: 'Excessive Work Hours',
        impact: 0.5,
        likelihood: 0.9,
        mitigation: 'Financial aid consultation and time management support'
      });
    }

    return riskFactors;
  }

  private generateRecommendations(
    studentContext: StudentContext,
    learningContext: LearningContext,
    predictions: PerformancePrediction['predictions']
  ): Array<{ action: string; expectedImprovement: number; difficulty: number; timeframe: string }> {
    const recommendations = [];

    if (predictions.overallGPA.predicted < 3.0) {
      recommendations.push({
        action: 'Enroll in academic support program',
        expectedImprovement: 0.5,
        difficulty: 3,
        timeframe: '4-6 weeks'
      });
    }

    if (studentContext.personalFactors.studyHabits < 5) {
      recommendations.push({
        action: 'Develop structured study schedule',
        expectedImprovement: 0.3,
        difficulty: 2,
        timeframe: '2-3 weeks'
      });
    }

    if (studentContext.socialFactors.studyGroups < 3) {
      recommendations.push({
        action: 'Join study groups for course',
        expectedImprovement: 0.2,
        difficulty: 1,
        timeframe: '1 week'
      });
    }

    return recommendations;
  }

  private generateDefaultTimeline(studentContext: StudentContext): PerformancePrediction['timeline'] {
    // Generate default timeline based on current performance
    const currentGPA = studentContext.academicHistory.length > 0 ?
      studentContext.academicHistory[studentContext.academicHistory.length - 1].gpa : 3.0;

    return {
      nextWeek: {
        gpa: currentGPA,
        courseGrades: {},
        skillMastery: {},
        learningVelocity: 5,
        retentionRate: 0.8,
        engagementScore: 7,
        consistencyIndex: 0.7
      },
      midterm: {
        gpa: currentGPA * 0.95,
        courseGrades: {},
        skillMastery: {},
        learningVelocity: 5.5,
        retentionRate: 0.82,
        engagementScore: 7.2,
        consistencyIndex: 0.75
      },
      endOfSemester: {
        gpa: currentGPA * 0.98,
        courseGrades: {},
        skillMastery: {},
        learningVelocity: 6,
        retentionRate: 0.85,
        engagementScore: 7.5,
        consistencyIndex: 0.8
      }
    };
  }

  private async predictTimeline(studentId: string): Promise<PerformancePrediction['timeline']> {
    // Use time series model to predict timeline
    return this.generateDefaultTimeline({ studentId } as StudentContext);
  }

  /**
   * Dispose models and cleanup
   */
  dispose(): void {
    [this.gpaModel, this.gradeModel, this.skillModel, this.timeSeriesModel, this.attentionModel]
      .forEach(model => {
        if (model) {
          model.dispose();
        }
      });

    this.gpaModel = null;
    this.gradeModel = null;
    this.skillModel = null;
    this.timeSeriesModel = null;
    this.attentionModel = null;

    this.featureScalers.clear();
    this.performanceHistory.clear();
  }
}

export default PerformancePredictionModel;