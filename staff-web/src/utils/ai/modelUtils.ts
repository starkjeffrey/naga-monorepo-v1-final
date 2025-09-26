/**
 * AI/ML Model Utilities
 *
 * Core utilities for working with TensorFlow.js models and predictions
 */

import * as tf from '@tensorflow/tfjs';
import { PredictionResult, StudentRiskFactor, StudentSuccessPrediction } from '../../types/innovation';

// Model loading and management
export class ModelManager {
  private static models: Map<string, tf.LayersModel> = new Map();
  private static modelMetadata: Map<string, any> = new Map();

  static async loadModel(modelId: string, modelUrl: string): Promise<tf.LayersModel> {
    try {
      if (this.models.has(modelId)) {
        return this.models.get(modelId)!;
      }

      console.log(`Loading model: ${modelId} from ${modelUrl}`);
      const model = await tf.loadLayersModel(modelUrl);
      this.models.set(modelId, model);

      // Store model metadata
      this.modelMetadata.set(modelId, {
        inputShape: model.inputs[0].shape,
        outputShape: model.outputs[0].shape,
        loadedAt: new Date(),
      });

      return model;
    } catch (error) {
      console.error(`Failed to load model ${modelId}:`, error);
      throw new Error(`Model loading failed: ${error}`);
    }
  }

  static getModel(modelId: string): tf.LayersModel | null {
    return this.models.get(modelId) || null;
  }

  static getModelMetadata(modelId: string): any {
    return this.modelMetadata.get(modelId) || null;
  }

  static disposeModel(modelId: string): void {
    const model = this.models.get(modelId);
    if (model) {
      model.dispose();
      this.models.delete(modelId);
      this.modelMetadata.delete(modelId);
    }
  }

  static disposeAllModels(): void {
    for (const [modelId] of this.models) {
      this.disposeModel(modelId);
    }
  }
}

// Data preprocessing utilities
export class DataPreprocessor {
  static normalizeFeatures(data: number[][], options: {
    method: 'minmax' | 'zscore' | 'robust';
    featureRanges?: Array<[number, number]>;
  } = { method: 'minmax' }): { normalized: number[][], stats: any } {
    const { method } = options;
    const stats: any = {};

    if (method === 'minmax') {
      const mins = data[0].map(() => Infinity);
      const maxs = data[0].map(() => -Infinity);

      // Find min and max for each feature
      data.forEach(row => {
        row.forEach((value, idx) => {
          mins[idx] = Math.min(mins[idx], value);
          maxs[idx] = Math.max(maxs[idx], value);
        });
      });

      stats.mins = mins;
      stats.maxs = maxs;

      // Normalize
      const normalized = data.map(row =>
        row.map((value, idx) => {
          const range = maxs[idx] - mins[idx];
          return range === 0 ? 0 : (value - mins[idx]) / range;
        })
      );

      return { normalized, stats };
    }

    if (method === 'zscore') {
      const means = data[0].map(() => 0);
      const stds = data[0].map(() => 0);

      // Calculate means
      data.forEach(row => {
        row.forEach((value, idx) => {
          means[idx] += value;
        });
      });
      means.forEach((sum, idx) => {
        means[idx] = sum / data.length;
      });

      // Calculate standard deviations
      data.forEach(row => {
        row.forEach((value, idx) => {
          stds[idx] += Math.pow(value - means[idx], 2);
        });
      });
      stds.forEach((sum, idx) => {
        stds[idx] = Math.sqrt(sum / data.length);
      });

      stats.means = means;
      stats.stds = stds;

      // Normalize
      const normalized = data.map(row =>
        row.map((value, idx) => {
          return stds[idx] === 0 ? 0 : (value - means[idx]) / stds[idx];
        })
      );

      return { normalized, stats };
    }

    throw new Error(`Unsupported normalization method: ${method}`);
  }

  static denormalizeFeatures(data: number[][], stats: any, method: 'minmax' | 'zscore'): number[][] {
    if (method === 'minmax') {
      const { mins, maxs } = stats;
      return data.map(row =>
        row.map((value, idx) => value * (maxs[idx] - mins[idx]) + mins[idx])
      );
    }

    if (method === 'zscore') {
      const { means, stds } = stats;
      return data.map(row =>
        row.map((value, idx) => value * stds[idx] + means[idx])
      );
    }

    throw new Error(`Unsupported denormalization method: ${method}`);
  }

  static oneHotEncode(categories: string[], vocabulary: string[]): number[][] {
    return categories.map(category => {
      const encoded = new Array(vocabulary.length).fill(0);
      const index = vocabulary.indexOf(category);
      if (index !== -1) {
        encoded[index] = 1;
      }
      return encoded;
    });
  }

  static createSequences(data: number[][], sequenceLength: number, stepSize: number = 1): number[][][] {
    const sequences: number[][][] = [];
    for (let i = 0; i <= data.length - sequenceLength; i += stepSize) {
      sequences.push(data.slice(i, i + sequenceLength));
    }
    return sequences;
  }
}

// Prediction utilities
export class PredictionEngine {
  static async predictStudentSuccess(
    studentData: any,
    modelId: string = 'student_success_v1'
  ): Promise<StudentSuccessPrediction> {
    try {
      const model = ModelManager.getModel(modelId);
      if (!model) {
        throw new Error(`Model ${modelId} not loaded`);
      }

      // Preprocess student data
      const features = this.extractStudentFeatures(studentData);
      const normalizedFeatures = this.normalizeStudentData(features);

      // Make prediction
      const tensor = tf.tensor2d([normalizedFeatures]);
      const prediction = model.predict(tensor) as tf.Tensor;
      const result = await prediction.data();

      // Cleanup tensors
      tensor.dispose();
      prediction.dispose();

      // Interpret results
      const graduationProbability = result[0];
      const nextTermGPA = result[1] || 0;
      const riskLevel = this.calculateRiskLevel(graduationProbability, studentData);
      const riskFactors = this.identifyRiskFactors(studentData, normalizedFeatures);
      const interventions = this.recommendInterventions(riskLevel, riskFactors);

      return {
        studentId: studentData.id,
        riskLevel,
        graduationProbability,
        nextTermGPA,
        riskFactors,
        interventions,
        lastUpdated: new Date(),
      };
    } catch (error) {
      console.error('Student success prediction failed:', error);
      throw error;
    }
  }

  private static extractStudentFeatures(studentData: any): number[] {
    return [
      studentData.currentGPA || 0,
      studentData.attendanceRate || 0,
      studentData.creditsCompleted || 0,
      studentData.totalCreditsRequired || 120,
      studentData.financialAidStatus ? 1 : 0,
      studentData.workHoursPerWeek || 0,
      studentData.distanceFromCampus || 0,
      studentData.parentEducationLevel || 0,
      studentData.firstGeneration ? 1 : 0,
      studentData.extracurricularCount || 0,
      studentData.tutoringSessions || 0,
      studentData.advisingMeetings || 0,
    ];
  }

  private static normalizeStudentData(features: number[]): number[] {
    // Simplified normalization - in production, use stored statistics
    const maxValues = [4.0, 1.0, 200, 200, 1, 40, 100, 6, 1, 10, 20, 10];
    return features.map((value, idx) => Math.min(value / maxValues[idx], 1));
  }

  private static calculateRiskLevel(probability: number, studentData: any): 'low' | 'medium' | 'high' | 'critical' {
    if (probability >= 0.8) return 'low';
    if (probability >= 0.6) return 'medium';
    if (probability >= 0.4) return 'high';
    return 'critical';
  }

  private static identifyRiskFactors(studentData: any, features: number[]): StudentRiskFactor[] {
    const factors: StudentRiskFactor[] = [];

    // Academic factors
    if (studentData.currentGPA < 2.5) {
      factors.push({
        category: 'academic',
        factor: 'Low GPA',
        impact: -0.8,
        confidence: 0.9,
        description: 'Current GPA is below academic standards',
        recommendation: 'Academic tutoring and study skills support',
      });
    }

    // Attendance factors
    if (studentData.attendanceRate < 0.8) {
      factors.push({
        category: 'attendance',
        factor: 'Poor Attendance',
        impact: -0.6,
        confidence: 0.85,
        description: 'Attendance rate is below acceptable threshold',
        recommendation: 'Attendance intervention program',
      });
    }

    // Financial factors
    if (!studentData.financialAidStatus && studentData.workHoursPerWeek > 30) {
      factors.push({
        category: 'financial',
        factor: 'Work-Study Balance',
        impact: -0.4,
        confidence: 0.7,
        description: 'High work hours may impact academic performance',
        recommendation: 'Financial aid counseling and time management support',
      });
    }

    return factors;
  }

  private static recommendInterventions(riskLevel: string, riskFactors: StudentRiskFactor[]): any[] {
    const interventions: any[] = [];

    if (riskLevel === 'critical' || riskLevel === 'high') {
      interventions.push({
        id: 'immediate_support',
        type: 'academic_support',
        title: 'Immediate Academic Intervention',
        description: 'Intensive tutoring and academic coaching',
        priority: 'urgent',
        estimatedImpact: 0.7,
        timeToImplement: '1 week',
        cost: 500,
        status: 'recommended',
        successRate: 0.75,
      });
    }

    // Add specific interventions based on risk factors
    riskFactors.forEach(factor => {
      if (factor.category === 'financial') {
        interventions.push({
          id: 'financial_counseling',
          type: 'financial_aid',
          title: 'Financial Aid Counseling',
          description: 'Meet with financial aid advisor to explore options',
          priority: 'high',
          estimatedImpact: 0.5,
          timeToImplement: '3 days',
          cost: 0,
          status: 'recommended',
          successRate: 0.6,
        });
      }
    });

    return interventions;
  }
}

// Model training utilities
export class ModelTrainer {
  static async trainSimpleModel(
    trainingData: number[][],
    labels: number[],
    options: {
      epochs?: number;
      batchSize?: number;
      validationSplit?: number;
      learningRate?: number;
    } = {}
  ): Promise<tf.LayersModel> {
    const {
      epochs = 100,
      batchSize = 32,
      validationSplit = 0.2,
      learningRate = 0.001,
    } = options;

    // Create model
    const model = tf.sequential({
      layers: [
        tf.layers.dense({ inputShape: [trainingData[0].length], units: 64, activation: 'relu' }),
        tf.layers.dropout({ rate: 0.3 }),
        tf.layers.dense({ units: 32, activation: 'relu' }),
        tf.layers.dropout({ rate: 0.2 }),
        tf.layers.dense({ units: 1, activation: 'sigmoid' }),
      ],
    });

    // Compile model
    model.compile({
      optimizer: tf.train.adam(learningRate),
      loss: 'binaryCrossentropy',
      metrics: ['accuracy'],
    });

    // Prepare tensors
    const xs = tf.tensor2d(trainingData);
    const ys = tf.tensor1d(labels);

    try {
      // Train model
      const history = await model.fit(xs, ys, {
        epochs,
        batchSize,
        validationSplit,
        shuffle: true,
        callbacks: {
          onEpochEnd: (epoch, logs) => {
            console.log(`Epoch ${epoch + 1}: loss = ${logs?.loss.toFixed(4)}, accuracy = ${logs?.acc?.toFixed(4)}`);
          },
        },
      });

      console.log('Training completed:', history);
      return model;
    } finally {
      // Cleanup tensors
      xs.dispose();
      ys.dispose();
    }
  }

  static async evaluateModel(
    model: tf.LayersModel,
    testData: number[][],
    testLabels: number[]
  ): Promise<{ accuracy: number; loss: number }> {
    const xs = tf.tensor2d(testData);
    const ys = tf.tensor1d(testLabels);

    try {
      const evaluation = model.evaluate(xs, ys) as tf.Tensor[];
      const loss = await evaluation[0].data();
      const accuracy = await evaluation[1].data();

      return {
        loss: loss[0],
        accuracy: accuracy[0],
      };
    } finally {
      xs.dispose();
      ys.dispose();
    }
  }
}

// Feature importance and model interpretation
export class ModelInterpreter {
  static async calculateFeatureImportance(
    model: tf.LayersModel,
    sampleData: number[][],
    featureNames: string[]
  ): Promise<Array<{ feature: string; importance: number }>> {
    const importances: Array<{ feature: string; importance: number }> = [];

    for (let i = 0; i < featureNames.length; i++) {
      const perturbedData = sampleData.map(row => {
        const newRow = [...row];
        newRow[i] = 0; // Zero out feature
        return newRow;
      });

      const originalTensor = tf.tensor2d(sampleData);
      const perturbedTensor = tf.tensor2d(perturbedData);

      const originalPreds = model.predict(originalTensor) as tf.Tensor;
      const perturbedPreds = model.predict(perturbedTensor) as tf.Tensor;

      const originalData = await originalPreds.data();
      const perturbedData_results = await perturbedPreds.data();

      // Calculate average change in prediction
      const avgChange = originalData.reduce((sum, orig, idx) => {
        return sum + Math.abs(orig - perturbedData_results[idx]);
      }, 0) / originalData.length;

      importances.push({
        feature: featureNames[i],
        importance: avgChange,
      });

      // Cleanup
      originalTensor.dispose();
      perturbedTensor.dispose();
      originalPreds.dispose();
      perturbedPreds.dispose();
    }

    return importances.sort((a, b) => b.importance - a.importance);
  }
}

// Memory management
export const cleanupTensors = () => {
  const numTensors = tf.memory().numTensors;
  console.log(`Current tensors in memory: ${numTensors}`);

  if (numTensors > 100) {
    console.warn('High tensor count detected. Consider disposing unused tensors.');
  }
};

// Export utilities
export const aiUtils = {
  ModelManager,
  DataPreprocessor,
  PredictionEngine,
  ModelTrainer,
  ModelInterpreter,
  cleanupTensors,
};