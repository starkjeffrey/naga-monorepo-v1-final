/**
 * Advanced Risk Assessment Models
 *
 * Sophisticated ML models for identifying and predicting student risks with:
 * - Multi-factor risk analysis
 * - Real-time risk scoring
 * - Intervention priority optimization
 * - Risk trend analysis
 * - Early warning systems
 */

import * as tf from '@tensorflow/tfjs';
import { DataPreprocessor } from '../../../../utils/ai/modelUtils';
import { StudentRiskFactor, Intervention } from '../../../../types/innovation';

export interface RiskAssessmentConfig {
  riskCategories: string[];
  alertThresholds: Record<string, number>;
  interventionMappings: Record<string, string[]>;
  timeHorizon: number; // days
  updateFrequency: number; // hours
}

export interface RiskScore {
  category: string;
  score: number; // 0-1
  confidence: number; // 0-1
  trend: 'improving' | 'stable' | 'deteriorating';
  factors: string[];
  urgency: 'low' | 'medium' | 'high' | 'critical';
  lastUpdated: Date;
}

export interface StudentRiskProfile {
  studentId: string;
  overallRisk: number;
  riskScores: RiskScore[];
  priorityInterventions: Intervention[];
  alertLevel: 'green' | 'yellow' | 'orange' | 'red';
  trends: {
    academic: number[];
    attendance: number[];
    financial: number[];
    behavioral: number[];
    social: number[];
  };
  predictions: {
    nextWeek: number;
    nextMonth: number;
    nextSemester: number;
  };
  lastAssessment: Date;
}

export class RiskAssessmentModel {
  private model: tf.LayersModel | null = null;
  private trendModel: tf.LayersModel | null = null;
  private config: RiskAssessmentConfig;
  private featureExtractors: Map<string, (data: any) => number[]> = new Map();
  private riskHistory: Map<string, RiskScore[]> = new Map();

  constructor(config: RiskAssessmentConfig) {
    this.config = config;
    this.initializeFeatureExtractors();
  }

  private initializeFeatureExtractors() {
    // Academic risk factors
    this.featureExtractors.set('academic', (data: any) => [
      data.currentGPA || 0,
      data.previousGPA || 0,
      data.gpaChange || 0,
      data.creditsCompleted || 0,
      data.creditsAttempted || 0,
      data.courseFailures || 0,
      data.courseWithdrawals || 0,
      data.academicProbation ? 1 : 0,
      data.timeToGraduation || 0,
      data.majorChanges || 0
    ]);

    // Attendance risk factors
    this.featureExtractors.set('attendance', (data: any) => [
      data.attendanceRate || 0,
      data.missedClasses || 0,
      data.lateArrivals || 0,
      data.excusedAbsences || 0,
      data.unexcusedAbsences || 0,
      data.attendanceTrend || 0,
      data.punctuality || 0,
      data.engagementLevel || 0
    ]);

    // Financial risk factors
    this.featureExtractors.set('financial', (data: any) => [
      data.outstandingBalance || 0,
      data.paymentHistory || 0,
      data.financialAid ? 1 : 0,
      data.scholarships || 0,
      data.workStudy ? 1 : 0,
      data.familyIncome || 0,
      data.dependents || 0,
      data.emergencyFund || 0,
      data.financialStress || 0
    ]);

    // Behavioral risk factors
    this.featureExtractors.set('behavioral', (data: any) => [
      data.disciplinaryActions || 0,
      data.counselingVisits || 0,
      data.stressLevel || 0,
      data.sleepQuality || 0,
      data.substanceUse || 0,
      data.mentalHealthConcerns || 0,
      data.socialIsolation || 0,
      data.motivationLevel || 0
    ]);

    // Social risk factors
    this.featureExtractors.set('social', (data: any) => [
      data.socialConnections || 0,
      data.extracurriculars || 0,
      data.campusInvolvement || 0,
      data.peerSupport || 0,
      data.familySupport || 0,
      data.culturalAdjustment || 0,
      data.languageBarrier ? 1 : 0,
      data.housingStability || 0
    ]);
  }

  /**
   * Create multi-output model for risk assessment
   */
  private createRiskModel(): tf.LayersModel {
    const totalFeatures = Array.from(this.featureExtractors.values())
      .reduce((total, extractor) => total + extractor({}).length, 0);

    const input = tf.input({ shape: [totalFeatures] });

    // Shared layers
    let x = tf.layers.dense({ units: 256, activation: 'relu' }).apply(input) as tf.SymbolicTensor;
    x = tf.layers.dropout({ rate: 0.3 }).apply(x) as tf.SymbolicTensor;
    x = tf.layers.dense({ units: 128, activation: 'relu' }).apply(x) as tf.SymbolicTensor;
    x = tf.layers.dropout({ rate: 0.2 }).apply(x) as tf.SymbolicTensor;

    // Category-specific outputs
    const outputs: tf.SymbolicTensor[] = [];
    const outputNames: string[] = [];

    this.config.riskCategories.forEach(category => {
      const categoryOutput = tf.layers.dense({
        units: 1,
        activation: 'sigmoid',
        name: `${category}_risk`
      }).apply(x) as tf.SymbolicTensor;

      outputs.push(categoryOutput);
      outputNames.push(`${category}_risk`);
    });

    // Overall risk output
    const overallRisk = tf.layers.dense({
      units: 1,
      activation: 'sigmoid',
      name: 'overall_risk'
    }).apply(x) as tf.SymbolicTensor;

    outputs.push(overallRisk);
    outputNames.push('overall_risk');

    return tf.model({ inputs: input, outputs });
  }

  /**
   * Train the risk assessment model
   */
  async trainModel(
    trainingData: Array<{ studentData: any; riskLabels: Record<string, number> }>,
    validationData?: Array<{ studentData: any; riskLabels: Record<string, number> }>
  ): Promise<void> {
    // Prepare training data
    const features = trainingData.map(item => this.extractAllFeatures(item.studentData));
    const labels = trainingData.map(item => {
      const categoryLabels = this.config.riskCategories.map(cat => item.riskLabels[cat] || 0);
      return [...categoryLabels, item.riskLabels.overall || 0];
    });

    // Normalize features
    const { normalized: normalizedFeatures, stats } = DataPreprocessor.normalizeFeatures(
      features,
      { method: 'zscore' }
    );

    // Create and compile model
    this.model = this.createRiskModel();

    const lossWeights: Record<string, number> = {};
    this.config.riskCategories.forEach(cat => {
      lossWeights[`${cat}_risk`] = 1.0;
    });
    lossWeights['overall_risk'] = 2.0; // Higher weight for overall risk

    this.model.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'binaryCrossentropy',
      metrics: ['accuracy', 'precision', 'recall'],
      lossWeights
    });

    // Prepare tensors
    const xs = tf.tensor2d(normalizedFeatures);
    const ys = tf.tensor2d(labels);

    // Train model
    await this.model.fit(xs, ys, {
      epochs: 150,
      batchSize: 32,
      validationSplit: 0.2,
      shuffle: true,
      callbacks: {
        onEpochEnd: (epoch, logs) => {
          console.log(`Risk Model Epoch ${epoch + 1}: loss = ${logs?.loss?.toFixed(4)}`);
        }
      }
    });

    // Cleanup
    xs.dispose();
    ys.dispose();

    console.log('Risk assessment model training completed');
  }

  /**
   * Assess risk for a student
   */
  async assessStudentRisk(studentData: any): Promise<StudentRiskProfile> {
    if (!this.model) {
      throw new Error('Risk model not trained');
    }

    const features = this.extractAllFeatures(studentData);
    const tensor = tf.tensor2d([features]);
    const prediction = this.model.predict(tensor) as tf.Tensor;
    const results = await prediction.data();

    // Cleanup
    tensor.dispose();
    prediction.dispose();

    // Parse results
    const riskScores: RiskScore[] = [];
    let overallRisk = 0;

    this.config.riskCategories.forEach((category, index) => {
      const score = results[index];
      const trend = this.calculateTrend(studentData.id, category, score);

      riskScores.push({
        category,
        score,
        confidence: this.calculateConfidence(category, studentData),
        trend,
        factors: this.identifyRiskFactors(category, studentData),
        urgency: this.calculateUrgency(score, trend),
        lastUpdated: new Date()
      });
    });

    overallRisk = results[this.config.riskCategories.length];

    // Store risk history
    this.updateRiskHistory(studentData.id, riskScores);

    // Generate interventions
    const priorityInterventions = this.generateInterventions(riskScores, studentData);

    // Calculate alert level
    const alertLevel = this.calculateAlertLevel(overallRisk, riskScores);

    // Generate predictions
    const predictions = await this.generateRiskPredictions(studentData.id, riskScores);

    return {
      studentId: studentData.id,
      overallRisk,
      riskScores,
      priorityInterventions,
      alertLevel,
      trends: this.getTrendData(studentData.id),
      predictions,
      lastAssessment: new Date()
    };
  }

  /**
   * Batch assess risks for multiple students
   */
  async batchAssessRisk(studentsData: any[]): Promise<StudentRiskProfile[]> {
    const profiles: StudentRiskProfile[] = [];

    for (const studentData of studentsData) {
      const profile = await this.assessStudentRisk(studentData);
      profiles.push(profile);
    }

    return profiles;
  }

  /**
   * Get students at high risk
   */
  async getHighRiskStudents(
    threshold: number = 0.7,
    category?: string
  ): Promise<Array<{ studentId: string; riskScore: number; category?: string }>> {
    // This would typically query a database or cache
    // For now, return mock data
    return [
      { studentId: 'student1', riskScore: 0.85, category: 'academic' },
      { studentId: 'student2', riskScore: 0.78, category: 'financial' }
    ];
  }

  /**
   * Update risk assessment for real-time monitoring
   */
  async updateRiskAssessment(
    studentId: string,
    newData: Partial<any>
  ): Promise<StudentRiskProfile> {
    // Merge new data with existing student data
    const existingData = await this.getStudentData(studentId);
    const updatedData = { ...existingData, ...newData };

    return this.assessStudentRisk(updatedData);
  }

  private extractAllFeatures(studentData: any): number[] {
    const allFeatures: number[] = [];

    this.config.riskCategories.forEach(category => {
      const extractor = this.featureExtractors.get(category);
      if (extractor) {
        const categoryFeatures = extractor(studentData);
        allFeatures.push(...categoryFeatures);
      }
    });

    return allFeatures;
  }

  private calculateTrend(
    studentId: string,
    category: string,
    currentScore: number
  ): 'improving' | 'stable' | 'deteriorating' {
    const history = this.riskHistory.get(studentId) || [];
    const categoryHistory = history
      .filter(h => h.category === category)
      .sort((a, b) => a.lastUpdated.getTime() - b.lastUpdated.getTime())
      .slice(-5); // Last 5 assessments

    if (categoryHistory.length < 2) {
      return 'stable';
    }

    const avgPrevious = categoryHistory.slice(0, -1)
      .reduce((sum, h) => sum + h.score, 0) / (categoryHistory.length - 1);

    const difference = currentScore - avgPrevious;

    if (difference > 0.1) return 'deteriorating';
    if (difference < -0.1) return 'improving';
    return 'stable';
  }

  private calculateConfidence(category: string, studentData: any): number {
    // Calculate confidence based on data completeness and quality
    const extractor = this.featureExtractors.get(category);
    if (!extractor) return 0.5;

    const features = extractor(studentData);
    const nonZeroFeatures = features.filter(f => f !== 0).length;
    const completeness = nonZeroFeatures / features.length;

    // Factor in data recency
    const dataAge = studentData.lastUpdated ?
      (Date.now() - new Date(studentData.lastUpdated).getTime()) / (1000 * 60 * 60 * 24) : 30;
    const recencyFactor = Math.max(0.5, 1 - (dataAge / 30)); // Decrease confidence for old data

    return Math.min(0.95, completeness * recencyFactor);
  }

  private identifyRiskFactors(category: string, studentData: any): string[] {
    const factors: string[] = [];

    switch (category) {
      case 'academic':
        if (studentData.currentGPA < 2.5) factors.push('Low GPA');
        if (studentData.courseFailures > 0) factors.push('Course Failures');
        if (studentData.academicProbation) factors.push('Academic Probation');
        break;

      case 'attendance':
        if (studentData.attendanceRate < 0.8) factors.push('Poor Attendance');
        if (studentData.unexcusedAbsences > 5) factors.push('Excessive Absences');
        break;

      case 'financial':
        if (studentData.outstandingBalance > 1000) factors.push('Outstanding Balance');
        if (!studentData.financialAid) factors.push('No Financial Aid');
        break;

      case 'behavioral':
        if (studentData.disciplinaryActions > 0) factors.push('Disciplinary Issues');
        if (studentData.stressLevel > 7) factors.push('High Stress Level');
        break;

      case 'social':
        if (studentData.socialConnections < 3) factors.push('Social Isolation');
        if (studentData.familySupport < 5) factors.push('Limited Family Support');
        break;
    }

    return factors;
  }

  private calculateUrgency(score: number, trend: string): 'low' | 'medium' | 'high' | 'critical' {
    if (score > 0.8 && trend === 'deteriorating') return 'critical';
    if (score > 0.7) return 'high';
    if (score > 0.5 || trend === 'deteriorating') return 'medium';
    return 'low';
  }

  private updateRiskHistory(studentId: string, riskScores: RiskScore[]): void {
    const existing = this.riskHistory.get(studentId) || [];
    const updated = [...existing, ...riskScores];

    // Keep only last 50 assessments
    const trimmed = updated.slice(-50);
    this.riskHistory.set(studentId, trimmed);
  }

  private generateInterventions(riskScores: RiskScore[], studentData: any): Intervention[] {
    const interventions: Intervention[] = [];

    riskScores.forEach(risk => {
      if (risk.urgency === 'critical' || risk.urgency === 'high') {
        const interventionTypes = this.config.interventionMappings[risk.category] || [];

        interventionTypes.forEach(type => {
          interventions.push({
            id: `${risk.category}_${type}_${Date.now()}`,
            type: type as any,
            title: this.getInterventionTitle(risk.category, type),
            description: this.getInterventionDescription(risk.category, type),
            priority: risk.urgency as any,
            estimatedImpact: this.calculateInterventionImpact(risk.category, type),
            timeToImplement: this.getTimeToImplement(type),
            cost: this.getInterventionCost(type),
            status: 'recommended',
            successRate: this.getSuccessRate(risk.category, type)
          });
        });
      }
    });

    // Sort by priority and impact
    return interventions.sort((a, b) => {
      const priorityOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      const aPriority = priorityOrder[a.priority as keyof typeof priorityOrder];
      const bPriority = priorityOrder[b.priority as keyof typeof priorityOrder];

      if (aPriority !== bPriority) {
        return bPriority - aPriority;
      }

      return b.estimatedImpact - a.estimatedImpact;
    });
  }

  private calculateAlertLevel(
    overallRisk: number,
    riskScores: RiskScore[]
  ): 'green' | 'yellow' | 'orange' | 'red' {
    const criticalRisks = riskScores.filter(r => r.urgency === 'critical').length;
    const highRisks = riskScores.filter(r => r.urgency === 'high').length;

    if (criticalRisks > 0 || overallRisk > 0.8) return 'red';
    if (highRisks > 1 || overallRisk > 0.6) return 'orange';
    if (highRisks > 0 || overallRisk > 0.4) return 'yellow';
    return 'green';
  }

  private async generateRiskPredictions(
    studentId: string,
    currentRisks: RiskScore[]
  ): Promise<{ nextWeek: number; nextMonth: number; nextSemester: number }> {
    // Simple trend-based prediction
    const overallTrend = currentRisks.reduce((sum, risk) => {
      const trendValue = risk.trend === 'improving' ? -0.1 :
                         risk.trend === 'deteriorating' ? 0.1 : 0;
      return sum + trendValue;
    }, 0) / currentRisks.length;

    const currentOverall = currentRisks.reduce((sum, risk) => sum + risk.score, 0) / currentRisks.length;

    return {
      nextWeek: Math.max(0, Math.min(1, currentOverall + (overallTrend * 0.1))),
      nextMonth: Math.max(0, Math.min(1, currentOverall + (overallTrend * 0.4))),
      nextSemester: Math.max(0, Math.min(1, currentOverall + (overallTrend * 1.5)))
    };
  }

  private getTrendData(studentId: string): StudentRiskProfile['trends'] {
    const history = this.riskHistory.get(studentId) || [];

    const trends: StudentRiskProfile['trends'] = {
      academic: [],
      attendance: [],
      financial: [],
      behavioral: [],
      social: []
    };

    this.config.riskCategories.forEach(category => {
      if (category in trends) {
        const categoryHistory = history
          .filter(h => h.category === category)
          .sort((a, b) => a.lastUpdated.getTime() - b.lastUpdated.getTime())
          .map(h => h.score);

        (trends as any)[category] = categoryHistory.slice(-10); // Last 10 data points
      }
    });

    return trends;
  }

  private async getStudentData(studentId: string): Promise<any> {
    // This would typically fetch from an API or database
    return {
      id: studentId,
      currentGPA: 3.2,
      attendanceRate: 0.85,
      // ... other data
    };
  }

  private getInterventionTitle(category: string, type: string): string {
    const titles: Record<string, Record<string, string>> = {
      academic: {
        tutoring: 'Academic Tutoring Support',
        counseling: 'Academic Counseling',
        study_skills: 'Study Skills Workshop'
      },
      financial: {
        counseling: 'Financial Aid Counseling',
        emergency_fund: 'Emergency Financial Assistance'
      }
    };

    return titles[category]?.[type] || `${category} ${type}`;
  }

  private getInterventionDescription(category: string, type: string): string {
    // Return appropriate description based on category and type
    return `Targeted intervention for ${category} risk factors through ${type}`;
  }

  private calculateInterventionImpact(category: string, type: string): number {
    // Return estimated impact based on historical data
    const impacts: Record<string, Record<string, number>> = {
      academic: { tutoring: 0.7, counseling: 0.5 },
      financial: { counseling: 0.6, emergency_fund: 0.8 }
    };

    return impacts[category]?.[type] || 0.5;
  }

  private getTimeToImplement(type: string): string {
    const times: Record<string, string> = {
      tutoring: '1 week',
      counseling: '3 days',
      emergency_fund: '1 day'
    };

    return times[type] || '1 week';
  }

  private getInterventionCost(type: string): number {
    const costs: Record<string, number> = {
      tutoring: 200,
      counseling: 0,
      emergency_fund: 500
    };

    return costs[type] || 100;
  }

  private getSuccessRate(category: string, type: string): number {
    // Return historical success rate
    return 0.75; // Default 75% success rate
  }

  /**
   * Dispose model and cleanup
   */
  dispose(): void {
    if (this.model) {
      this.model.dispose();
      this.model = null;
    }

    if (this.trendModel) {
      this.trendModel.dispose();
      this.trendModel = null;
    }

    this.riskHistory.clear();
  }
}

export default RiskAssessmentModel;