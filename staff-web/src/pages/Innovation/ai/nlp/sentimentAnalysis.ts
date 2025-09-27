/**
 * Advanced Sentiment Analysis Service
 *
 * Comprehensive sentiment analysis for educational communications with:
 * - Multi-language sentiment detection
 * - Academic-specific sentiment modeling
 * - Emotion detection and stress indicators
 * - Context-aware analysis for educational settings
 * - Real-time sentiment monitoring
 */

import * as tf from '@tensorflow/tfjs';

export interface SentimentResult {
  polarity: 'positive' | 'negative' | 'neutral';
  confidence: number;
  score: number; // -1 to 1
  emotions: {
    joy: number;
    sadness: number;
    anger: number;
    fear: number;
    disgust: number;
    surprise: number;
    trust: number;
    anticipation: number;
  };
  academicContext: {
    stress: number;
    engagement: number;
    confusion: number;
    satisfaction: number;
    motivation: number;
  };
  urgency: 'low' | 'medium' | 'high' | 'critical';
  keywords: Array<{
    word: string;
    sentiment: number;
    importance: number;
  }>;
  language: string;
  detectedTopics: string[];
}

export interface ConversationAnalysis {
  conversationId: string;
  participants: string[];
  overallSentiment: SentimentResult;
  sentimentTimeline: Array<{
    timestamp: Date;
    sentiment: SentimentResult;
    messageId: string;
    userId: string;
  }>;
  riskIndicators: Array<{
    type: 'academic_stress' | 'emotional_distress' | 'disengagement' | 'confusion';
    severity: number;
    evidence: string[];
    recommendation: string;
  }>;
  insights: {
    dominantEmotion: string;
    engagementLevel: number;
    supportNeeded: boolean;
    interventionSuggested: boolean;
  };
}

export interface TextClassification {
  categories: Array<{
    category: string;
    confidence: number;
    subcategories: Array<{
      name: string;
      confidence: number;
    }>;
  }>;
  intent: {
    primary: string;
    confidence: number;
    alternatives: Array<{
      intent: string;
      confidence: number;
    }>;
  };
  entities: Array<{
    text: string;
    type: 'PERSON' | 'COURSE' | 'DATE' | 'GRADE' | 'LOCATION' | 'ORGANIZATION';
    startIndex: number;
    endIndex: number;
    confidence: number;
  }>;
}

export class SentimentAnalysisService {
  private sentimentModel: tf.LayersModel | null = null;
  private emotionModel: tf.LayersModel | null = null;
  private academicModel: tf.LayersModel | null = null;
  private languageModel: tf.LayersModel | null = null;
  private vocabulary: Map<string, number> = new Map();
  private academicKeywords: Set<string> = new Set();
  private emotionLexicon: Map<string, Record<string, number>> = new Map();
  private maxSequenceLength = 128;

  constructor() {
    this.initializeModels();
    this.loadAcademicKeywords();
    this.loadEmotionLexicon();
  }

  private async initializeModels(): Promise<void> {
    console.log('Initializing sentiment analysis models...');
    await this.createSentimentModel();
    await this.createEmotionModel();
    await this.createAcademicContextModel();
  }

  private async createSentimentModel(): Promise<void> {
    // Create sentiment classification model
    this.sentimentModel = tf.sequential({
      layers: [
        tf.layers.embedding({
          inputDim: 10000, // vocabulary size
          outputDim: 128,
          inputLength: this.maxSequenceLength
        }),
        tf.layers.dropout({ rate: 0.5 }),
        tf.layers.lstm({
          units: 64,
          dropout: 0.5,
          recurrentDropout: 0.5,
          returnSequences: true
        }),
        tf.layers.lstm({
          units: 32,
          dropout: 0.5,
          recurrentDropout: 0.5
        }),
        tf.layers.dense({ units: 16, activation: 'relu' }),
        tf.layers.dropout({ rate: 0.5 }),
        tf.layers.dense({ units: 3, activation: 'softmax' }) // positive, negative, neutral
      ]
    });

    this.sentimentModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'categoricalCrossentropy',
      metrics: ['accuracy']
    });

    console.log('Sentiment model created');
  }

  private async createEmotionModel(): Promise<void> {
    // Create emotion detection model
    this.emotionModel = tf.sequential({
      layers: [
        tf.layers.embedding({
          inputDim: 10000,
          outputDim: 100,
          inputLength: this.maxSequenceLength
        }),
        tf.layers.spatialDropout1d({ rate: 0.4 }),
        tf.layers.bidirectional({
          layer: tf.layers.lstm({
            units: 64,
            dropout: 0.5,
            recurrentDropout: 0.5
          })
        }),
        tf.layers.dense({ units: 64, activation: 'relu' }),
        tf.layers.dropout({ rate: 0.5 }),
        tf.layers.dense({ units: 8, activation: 'sigmoid' }) // 8 emotions (Plutchik's wheel)
      ]
    });

    this.emotionModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'binaryCrossentropy',
      metrics: ['accuracy']
    });

    console.log('Emotion model created');
  }

  private async createAcademicContextModel(): Promise<void> {
    // Create academic context analysis model
    this.academicModel = tf.sequential({
      layers: [
        tf.layers.embedding({
          inputDim: 10000,
          outputDim: 150,
          inputLength: this.maxSequenceLength
        }),
        tf.layers.dropout({ rate: 0.3 }),
        tf.layers.conv1d({
          filters: 128,
          kernelSize: 3,
          activation: 'relu'
        }),
        tf.layers.globalMaxPooling1d(),
        tf.layers.dense({ units: 128, activation: 'relu' }),
        tf.layers.dropout({ rate: 0.5 }),
        tf.layers.dense({ units: 64, activation: 'relu' }),
        tf.layers.dense({ units: 5, activation: 'sigmoid' }) // stress, engagement, confusion, satisfaction, motivation
      ]
    });

    this.academicModel.compile({
      optimizer: tf.train.adam(0.001),
      loss: 'meanSquaredError',
      metrics: ['mae']
    });

    console.log('Academic context model created');
  }

  /**
   * Analyze sentiment of a single text message
   */
  async analyzeSentiment(
    text: string,
    context?: {
      userId?: string;
      conversationId?: string;
      messageType?: 'question' | 'response' | 'announcement' | 'feedback';
      academicContext?: 'assignment' | 'grade' | 'general' | 'support';
    }
  ): Promise<SentimentResult> {
    // Preprocess text
    const preprocessedText = this.preprocessText(text);
    const tokens = this.tokenizeText(preprocessedText);
    const sequence = this.textToSequence(tokens);

    // Detect language
    const language = this.detectLanguage(text);

    // Get sentiment prediction
    const sentimentPrediction = await this.predictSentiment(sequence);

    // Get emotion prediction
    const emotionPrediction = await this.predictEmotions(sequence);

    // Get academic context prediction
    const academicPrediction = await this.predictAcademicContext(sequence);

    // Extract keywords and their sentiment contributions
    const keywords = this.extractSentimentKeywords(preprocessedText, sentimentPrediction.score);

    // Detect topics
    const detectedTopics = this.detectTopics(preprocessedText);

    // Calculate urgency based on sentiment and academic context
    const urgency = this.calculateUrgency(sentimentPrediction, academicPrediction, context);

    return {
      polarity: sentimentPrediction.polarity,
      confidence: sentimentPrediction.confidence,
      score: sentimentPrediction.score,
      emotions: emotionPrediction,
      academicContext: academicPrediction,
      urgency,
      keywords,
      language,
      detectedTopics
    };
  }

  /**
   * Analyze conversation sentiment over time
   */
  async analyzeConversation(
    messages: Array<{
      id: string;
      text: string;
      userId: string;
      timestamp: Date;
      messageType?: string;
    }>,
    conversationId: string
  ): Promise<ConversationAnalysis> {
    const sentimentTimeline: ConversationAnalysis['sentimentTimeline'] = [];
    const allSentiments: SentimentResult[] = [];

    // Analyze each message
    for (const message of messages) {
      const sentiment = await this.analyzeSentiment(message.text, {
        userId: message.userId,
        conversationId,
        messageType: message.messageType as any
      });

      sentimentTimeline.push({
        timestamp: message.timestamp,
        sentiment,
        messageId: message.id,
        userId: message.userId
      });

      allSentiments.push(sentiment);
    }

    // Calculate overall conversation sentiment
    const overallSentiment = this.aggregateSentiments(allSentiments);

    // Identify risk indicators
    const riskIndicators = this.identifyRiskIndicators(sentimentTimeline);

    // Generate insights
    const insights = this.generateConversationInsights(sentimentTimeline, overallSentiment);

    return {
      conversationId,
      participants: [...new Set(messages.map(m => m.userId))],
      overallSentiment,
      sentimentTimeline,
      riskIndicators,
      insights
    };
  }

  /**
   * Classify text into categories and extract intent
   */
  async classifyText(text: string): Promise<TextClassification> {
    const preprocessedText = this.preprocessText(text);

    // Academic category classification
    const categories = await this.classifyAcademicCategories(preprocessedText);

    // Intent detection
    const intent = await this.detectIntent(preprocessedText);

    // Named entity recognition
    const entities = await this.extractEntities(preprocessedText);

    return {
      categories,
      intent,
      entities
    };
  }

  /**
   * Batch analyze multiple texts
   */
  async batchAnalyzeSentiment(
    texts: Array<{
      text: string;
      id: string;
      context?: any;
    }>
  ): Promise<Array<{ id: string; result: SentimentResult }>> {
    const results: Array<{ id: string; result: SentimentResult }> = [];

    for (const item of texts) {
      const result = await this.analyzeSentiment(item.text, item.context);
      results.push({ id: item.id, result });
    }

    return results;
  }

  /**
   * Monitor sentiment trends for a user over time
   */
  async monitorUserSentiment(
    userId: string,
    timeframe: 'day' | 'week' | 'month' | 'semester'
  ): Promise<{
    trends: Array<{
      date: Date;
      avgSentiment: number;
      emotionalState: string;
      riskLevel: number;
    }>;
    insights: {
      overallTrend: 'improving' | 'stable' | 'declining';
      riskFactors: string[];
      recommendations: string[];
    };
  }> {
    // This would typically fetch historical data from a database
    // For now, return mock data structure
    return {
      trends: [
        {
          date: new Date(),
          avgSentiment: 0.3,
          emotionalState: 'slightly_positive',
          riskLevel: 0.2
        }
      ],
      insights: {
        overallTrend: 'stable',
        riskFactors: [],
        recommendations: ['Continue current engagement level']
      }
    };
  }

  private preprocessText(text: string): string {
    return text
      .toLowerCase()
      .replace(/[^\w\s]/g, ' ') // Remove punctuation
      .replace(/\s+/g, ' ') // Normalize whitespace
      .trim();
  }

  private tokenizeText(text: string): string[] {
    return text.split(' ').filter(token => token.length > 0);
  }

  private textToSequence(tokens: string[]): number[] {
    const sequence = tokens.map(token => this.vocabulary.get(token) || 0);

    // Pad or truncate to maxSequenceLength
    if (sequence.length > this.maxSequenceLength) {
      return sequence.slice(0, this.maxSequenceLength);
    } else {
      return [...sequence, ...Array(this.maxSequenceLength - sequence.length).fill(0)];
    }
  }

  private async predictSentiment(sequence: number[]): Promise<{
    polarity: 'positive' | 'negative' | 'neutral';
    confidence: number;
    score: number;
  }> {
    if (!this.sentimentModel) {
      return { polarity: 'neutral', confidence: 0.5, score: 0 };
    }

    const input = tf.tensor2d([sequence]);
    const prediction = this.sentimentModel.predict(input) as tf.Tensor;
    const probabilities = await prediction.data();

    input.dispose();
    prediction.dispose();

    const [negativeProb, neutralProb, positiveProb] = Array.from(probabilities);
    const maxProb = Math.max(negativeProb, neutralProb, positiveProb);

    let polarity: 'positive' | 'negative' | 'neutral';
    if (maxProb === positiveProb) {
      polarity = 'positive';
    } else if (maxProb === negativeProb) {
      polarity = 'negative';
    } else {
      polarity = 'neutral';
    }

    const score = positiveProb - negativeProb; // -1 to 1 scale

    return {
      polarity,
      confidence: maxProb,
      score
    };
  }

  private async predictEmotions(sequence: number[]): Promise<SentimentResult['emotions']> {
    if (!this.emotionModel) {
      return {
        joy: 0, sadness: 0, anger: 0, fear: 0,
        disgust: 0, surprise: 0, trust: 0, anticipation: 0
      };
    }

    const input = tf.tensor2d([sequence]);
    const prediction = this.emotionModel.predict(input) as tf.Tensor;
    const emotions = await prediction.data();

    input.dispose();
    prediction.dispose();

    return {
      joy: emotions[0],
      sadness: emotions[1],
      anger: emotions[2],
      fear: emotions[3],
      disgust: emotions[4],
      surprise: emotions[5],
      trust: emotions[6],
      anticipation: emotions[7]
    };
  }

  private async predictAcademicContext(sequence: number[]): Promise<SentimentResult['academicContext']> {
    if (!this.academicModel) {
      return {
        stress: 0, engagement: 0, confusion: 0,
        satisfaction: 0, motivation: 0
      };
    }

    const input = tf.tensor2d([sequence]);
    const prediction = this.academicModel.predict(input) as tf.Tensor;
    const context = await prediction.data();

    input.dispose();
    prediction.dispose();

    return {
      stress: context[0],
      engagement: context[1],
      confusion: context[2],
      satisfaction: context[3],
      motivation: context[4]
    };
  }

  private extractSentimentKeywords(text: string, sentimentScore: number): SentimentResult['keywords'] {
    const words = text.split(' ');
    const keywords: SentimentResult['keywords'] = [];

    for (const word of words) {
      if (this.academicKeywords.has(word) || word.length > 4) {
        const emotionScores = this.emotionLexicon.get(word);
        if (emotionScores) {
          const wordSentiment = (emotionScores.positive || 0) - (emotionScores.negative || 0);
          keywords.push({
            word,
            sentiment: wordSentiment,
            importance: Math.abs(wordSentiment) * 0.5 + (this.academicKeywords.has(word) ? 0.5 : 0)
          });
        }
      }
    }

    return keywords
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 10); // Top 10 keywords
  }

  private detectTopics(text: string): string[] {
    const academicTopics = [
      'assignment', 'exam', 'grade', 'course', 'professor', 'homework',
      'study', 'test', 'project', 'deadline', 'feedback', 'help',
      'tutoring', 'office hours', 'schedule', 'registration'
    ];

    const detectedTopics: string[] = [];

    for (const topic of academicTopics) {
      if (text.includes(topic)) {
        detectedTopics.push(topic);
      }
    }

    return detectedTopics;
  }

  private detectLanguage(text: string): string {
    // Simple language detection based on common words
    const englishWords = ['the', 'and', 'is', 'in', 'to', 'of', 'a', 'that', 'it', 'with'];
    const spanishWords = ['el', 'la', 'de', 'que', 'y', 'en', 'un', 'es', 'se', 'no'];
    const frenchWords = ['le', 'la', 'les', 'de', 'et', 'en', 'un', 'une', 'du', 'que'];

    const words = text.toLowerCase().split(' ');

    let englishCount = 0;
    let spanishCount = 0;
    let frenchCount = 0;

    for (const word of words) {
      if (englishWords.includes(word)) englishCount++;
      if (spanishWords.includes(word)) spanishCount++;
      if (frenchWords.includes(word)) frenchCount++;
    }

    if (englishCount >= spanishCount && englishCount >= frenchCount) return 'en';
    if (spanishCount >= frenchCount) return 'es';
    return 'fr';
  }

  private calculateUrgency(
    sentiment: any,
    academic: any,
    context?: any
  ): 'low' | 'medium' | 'high' | 'critical' {
    let urgencyScore = 0;

    // Negative sentiment increases urgency
    if (sentiment.score < -0.5) urgencyScore += 0.3;
    else if (sentiment.score < -0.2) urgencyScore += 0.1;

    // High stress increases urgency
    if (academic.stress > 0.7) urgencyScore += 0.4;
    else if (academic.stress > 0.5) urgencyScore += 0.2;

    // High confusion increases urgency
    if (academic.confusion > 0.6) urgencyScore += 0.3;

    // Low engagement/motivation increases urgency
    if (academic.engagement < 0.3 || academic.motivation < 0.3) urgencyScore += 0.2;

    if (urgencyScore > 0.8) return 'critical';
    if (urgencyScore > 0.5) return 'high';
    if (urgencyScore > 0.2) return 'medium';
    return 'low';
  }

  private aggregateSentiments(sentiments: SentimentResult[]): SentimentResult {
    if (sentiments.length === 0) {
      return {
        polarity: 'neutral',
        confidence: 0,
        score: 0,
        emotions: { joy: 0, sadness: 0, anger: 0, fear: 0, disgust: 0, surprise: 0, trust: 0, anticipation: 0 },
        academicContext: { stress: 0, engagement: 0, confusion: 0, satisfaction: 0, motivation: 0 },
        urgency: 'low',
        keywords: [],
        language: 'en',
        detectedTopics: []
      };
    }

    // Calculate average values
    const avgScore = sentiments.reduce((sum, s) => sum + s.score, 0) / sentiments.length;
    const avgConfidence = sentiments.reduce((sum, s) => sum + s.confidence, 0) / sentiments.length;

    // Aggregate emotions
    const emotions: SentimentResult['emotions'] = {
      joy: sentiments.reduce((sum, s) => sum + s.emotions.joy, 0) / sentiments.length,
      sadness: sentiments.reduce((sum, s) => sum + s.emotions.sadness, 0) / sentiments.length,
      anger: sentiments.reduce((sum, s) => sum + s.emotions.anger, 0) / sentiments.length,
      fear: sentiments.reduce((sum, s) => sum + s.emotions.fear, 0) / sentiments.length,
      disgust: sentiments.reduce((sum, s) => sum + s.emotions.disgust, 0) / sentiments.length,
      surprise: sentiments.reduce((sum, s) => sum + s.emotions.surprise, 0) / sentiments.length,
      trust: sentiments.reduce((sum, s) => sum + s.emotions.trust, 0) / sentiments.length,
      anticipation: sentiments.reduce((sum, s) => sum + s.emotions.anticipation, 0) / sentiments.length
    };

    // Aggregate academic context
    const academicContext: SentimentResult['academicContext'] = {
      stress: sentiments.reduce((sum, s) => sum + s.academicContext.stress, 0) / sentiments.length,
      engagement: sentiments.reduce((sum, s) => sum + s.academicContext.engagement, 0) / sentiments.length,
      confusion: sentiments.reduce((sum, s) => sum + s.academicContext.confusion, 0) / sentiments.length,
      satisfaction: sentiments.reduce((sum, s) => sum + s.academicContext.satisfaction, 0) / sentiments.length,
      motivation: sentiments.reduce((sum, s) => sum + s.academicContext.motivation, 0) / sentiments.length
    };

    // Determine overall polarity
    let polarity: 'positive' | 'negative' | 'neutral';
    if (avgScore > 0.1) polarity = 'positive';
    else if (avgScore < -0.1) polarity = 'negative';
    else polarity = 'neutral';

    // Find most urgent level
    const urgencyLevels = { low: 0, medium: 1, high: 2, critical: 3 };
    const maxUrgency = Math.max(...sentiments.map(s => urgencyLevels[s.urgency]));
    const urgency = Object.keys(urgencyLevels)[maxUrgency] as 'low' | 'medium' | 'high' | 'critical';

    // Aggregate keywords
    const allKeywords = sentiments.flatMap(s => s.keywords);
    const keywordMap = new Map<string, { sentiment: number; importance: number; count: number }>();

    for (const keyword of allKeywords) {
      const existing = keywordMap.get(keyword.word);
      if (existing) {
        existing.sentiment = (existing.sentiment * existing.count + keyword.sentiment) / (existing.count + 1);
        existing.importance = Math.max(existing.importance, keyword.importance);
        existing.count++;
      } else {
        keywordMap.set(keyword.word, {
          sentiment: keyword.sentiment,
          importance: keyword.importance,
          count: 1
        });
      }
    }

    const keywords = Array.from(keywordMap.entries())
      .map(([word, data]) => ({
        word,
        sentiment: data.sentiment,
        importance: data.importance * Math.log(data.count + 1) // Weight by frequency
      }))
      .sort((a, b) => b.importance - a.importance)
      .slice(0, 10);

    // Aggregate topics
    const allTopics = sentiments.flatMap(s => s.detectedTopics);
    const detectedTopics = [...new Set(allTopics)];

    // Most common language
    const languageCounts = new Map<string, number>();
    sentiments.forEach(s => {
      languageCounts.set(s.language, (languageCounts.get(s.language) || 0) + 1);
    });
    const language = Array.from(languageCounts.entries())
      .sort((a, b) => b[1] - a[1])[0]?.[0] || 'en';

    return {
      polarity,
      confidence: avgConfidence,
      score: avgScore,
      emotions,
      academicContext,
      urgency,
      keywords,
      language,
      detectedTopics
    };
  }

  private identifyRiskIndicators(timeline: ConversationAnalysis['sentimentTimeline']): ConversationAnalysis['riskIndicators'] {
    const indicators: ConversationAnalysis['riskIndicators'] = [];

    // Check for sustained stress
    const recentMessages = timeline.slice(-5);
    const avgStress = recentMessages.reduce((sum, msg) => sum + msg.sentiment.academicContext.stress, 0) / recentMessages.length;

    if (avgStress > 0.7) {
      indicators.push({
        type: 'academic_stress',
        severity: avgStress,
        evidence: recentMessages.filter(msg => msg.sentiment.academicContext.stress > 0.7).map(msg => msg.messageId),
        recommendation: 'Consider academic support or stress management resources'
      });
    }

    // Check for emotional distress
    const avgSadness = recentMessages.reduce((sum, msg) => sum + msg.sentiment.emotions.sadness, 0) / recentMessages.length;
    const avgAnger = recentMessages.reduce((sum, msg) => sum + msg.sentiment.emotions.anger, 0) / recentMessages.length;

    if (avgSadness > 0.6 || avgAnger > 0.6) {
      indicators.push({
        type: 'emotional_distress',
        severity: Math.max(avgSadness, avgAnger),
        evidence: recentMessages.filter(msg => msg.sentiment.emotions.sadness > 0.6 || msg.sentiment.emotions.anger > 0.6).map(msg => msg.messageId),
        recommendation: 'Consider counseling or mental health support'
      });
    }

    // Check for disengagement
    const avgEngagement = recentMessages.reduce((sum, msg) => sum + msg.sentiment.academicContext.engagement, 0) / recentMessages.length;

    if (avgEngagement < 0.3) {
      indicators.push({
        type: 'disengagement',
        severity: 1 - avgEngagement,
        evidence: recentMessages.filter(msg => msg.sentiment.academicContext.engagement < 0.3).map(msg => msg.messageId),
        recommendation: 'Implement engagement strategies or check in with student'
      });
    }

    // Check for confusion
    const avgConfusion = recentMessages.reduce((sum, msg) => sum + msg.sentiment.academicContext.confusion, 0) / recentMessages.length;

    if (avgConfusion > 0.6) {
      indicators.push({
        type: 'confusion',
        severity: avgConfusion,
        evidence: recentMessages.filter(msg => msg.sentiment.academicContext.confusion > 0.6).map(msg => msg.messageId),
        recommendation: 'Provide additional clarification or tutoring support'
      });
    }

    return indicators;
  }

  private generateConversationInsights(
    timeline: ConversationAnalysis['sentimentTimeline'],
    overallSentiment: SentimentResult
  ): ConversationAnalysis['insights'] {
    // Find dominant emotion
    const emotions = overallSentiment.emotions;
    const dominantEmotion = Object.entries(emotions)
      .sort((a, b) => b[1] - a[1])[0][0];

    // Calculate engagement level
    const engagementLevel = overallSentiment.academicContext.engagement;

    // Determine if support is needed
    const supportNeeded = overallSentiment.academicContext.stress > 0.6 ||
                          overallSentiment.academicContext.confusion > 0.6 ||
                          overallSentiment.score < -0.3;

    // Determine if intervention is suggested
    const interventionSuggested = overallSentiment.urgency === 'high' ||
                                  overallSentiment.urgency === 'critical';

    return {
      dominantEmotion,
      engagementLevel,
      supportNeeded,
      interventionSuggested
    };
  }

  private async classifyAcademicCategories(text: string): Promise<TextClassification['categories']> {
    // Mock academic category classification
    const categories = [
      'academic_support', 'technical_issues', 'administrative', 'course_content',
      'scheduling', 'grades', 'feedback', 'general_inquiry'
    ];

    // Simple keyword-based classification (would be ML-based in production)
    const scores: Record<string, number> = {};

    categories.forEach(category => {
      scores[category] = Math.random() * 0.5 + 0.1; // Mock scores
    });

    // Boost scores based on keywords
    if (text.includes('grade') || text.includes('score')) {
      scores['grades'] = Math.min(1, scores['grades'] + 0.4);
    }
    if (text.includes('help') || text.includes('support')) {
      scores['academic_support'] = Math.min(1, scores['academic_support'] + 0.4);
    }
    if (text.includes('schedule') || text.includes('time')) {
      scores['scheduling'] = Math.min(1, scores['scheduling'] + 0.4);
    }

    return Object.entries(scores)
      .map(([category, confidence]) => ({
        category,
        confidence,
        subcategories: [] // Would be filled with more specific classifications
      }))
      .sort((a, b) => b.confidence - a.confidence)
      .slice(0, 3);
  }

  private async detectIntent(text: string): Promise<TextClassification['intent']> {
    const intents = [
      'question', 'complaint', 'request', 'information', 'compliment',
      'emergency', 'feedback', 'scheduling', 'technical_support'
    ];

    // Simple intent detection (would be ML-based in production)
    const scores: Record<string, number> = {};

    intents.forEach(intent => {
      scores[intent] = Math.random() * 0.3 + 0.1;
    });

    // Boost based on text patterns
    if (text.includes('?') || text.includes('how') || text.includes('what') || text.includes('when') || text.includes('where')) {
      scores['question'] = Math.min(1, scores['question'] + 0.5);
    }
    if (text.includes('please') || text.includes('can you') || text.includes('could you')) {
      scores['request'] = Math.min(1, scores['request'] + 0.4);
    }
    if (text.includes('problem') || text.includes('issue') || text.includes('wrong')) {
      scores['complaint'] = Math.min(1, scores['complaint'] + 0.4);
    }

    const sortedIntents = Object.entries(scores)
      .sort((a, b) => b[1] - a[1]);

    return {
      primary: sortedIntents[0][0],
      confidence: sortedIntents[0][1],
      alternatives: sortedIntents.slice(1, 3).map(([intent, confidence]) => ({
        intent,
        confidence
      }))
    };
  }

  private async extractEntities(text: string): Promise<TextClassification['entities']> {
    const entities: TextClassification['entities'] = [];

    // Simple pattern-based entity extraction
    const patterns = {
      PERSON: /\b[A-Z][a-z]+ [A-Z][a-z]+\b/g,
      COURSE: /\b[A-Z]{2,4}\s?\d{3,4}\b/g,
      DATE: /\b\d{1,2}\/\d{1,2}\/\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{2,4}\b/g,
      GRADE: /\b[A-F][+-]?\b|\b\d{1,3}(?:\.\d{1,2})?%\b/g
    };

    Object.entries(patterns).forEach(([type, pattern]) => {
      const matches = text.matchAll(pattern);
      for (const match of matches) {
        if (match.index !== undefined) {
          entities.push({
            text: match[0],
            type: type as any,
            startIndex: match.index,
            endIndex: match.index + match[0].length,
            confidence: 0.8
          });
        }
      }
    });

    return entities;
  }

  private loadAcademicKeywords(): void {
    const keywords = [
      'assignment', 'homework', 'quiz', 'exam', 'test', 'grade', 'score',
      'professor', 'instructor', 'teacher', 'tutor', 'course', 'class',
      'lecture', 'seminar', 'lab', 'study', 'research', 'paper', 'essay',
      'project', 'presentation', 'deadline', 'due', 'submit', 'upload',
      'feedback', 'review', 'revision', 'draft', 'final', 'midterm',
      'semester', 'quarter', 'term', 'schedule', 'timetable', 'calendar',
      'registration', 'enrollment', 'prerequisite', 'credit', 'unit',
      'gpa', 'cgpa', 'transcript', 'degree', 'major', 'minor', 'elective',
      'required', 'optional', 'mandatory', 'attendance', 'absent', 'late',
      'office hours', 'consultation', 'help', 'support', 'tutoring',
      'library', 'resources', 'textbook', 'material', 'reading',
      'online', 'virtual', 'campus', 'classroom', 'auditorium',
      'confused', 'difficult', 'easy', 'challenging', 'interesting',
      'boring', 'stressful', 'anxious', 'worried', 'excited', 'motivated'
    ];

    keywords.forEach(keyword => this.academicKeywords.add(keyword));
  }

  private loadEmotionLexicon(): void {
    // Simplified emotion lexicon
    const lexicon = {
      'excellent': { positive: 0.8, joy: 0.7 },
      'great': { positive: 0.7, joy: 0.6 },
      'good': { positive: 0.6, joy: 0.4 },
      'bad': { negative: 0.6, sadness: 0.4 },
      'terrible': { negative: 0.8, anger: 0.6 },
      'awful': { negative: 0.7, disgust: 0.5 },
      'confused': { negative: 0.4, fear: 0.3 },
      'worried': { negative: 0.5, fear: 0.6 },
      'stressed': { negative: 0.6, fear: 0.5 },
      'excited': { positive: 0.7, anticipation: 0.8 },
      'happy': { positive: 0.8, joy: 0.9 },
      'sad': { negative: 0.7, sadness: 0.8 },
      'angry': { negative: 0.8, anger: 0.9 },
      'frustrated': { negative: 0.6, anger: 0.7 },
      'disappointed': { negative: 0.5, sadness: 0.6 },
      'satisfied': { positive: 0.6, joy: 0.5 },
      'pleased': { positive: 0.7, joy: 0.6 },
      'grateful': { positive: 0.8, trust: 0.7 },
      'thankful': { positive: 0.8, trust: 0.7 },
      'help': { neutral: 0.3, trust: 0.4 },
      'support': { positive: 0.4, trust: 0.5 }
    };

    Object.entries(lexicon).forEach(([word, scores]) => {
      this.emotionLexicon.set(word, scores);
    });
  }

  /**
   * Dispose models and cleanup
   */
  dispose(): void {
    [this.sentimentModel, this.emotionModel, this.academicModel, this.languageModel]
      .forEach(model => {
        if (model) {
          model.dispose();
        }
      });

    this.sentimentModel = null;
    this.emotionModel = null;
    this.academicModel = null;
    this.languageModel = null;

    this.vocabulary.clear();
    this.academicKeywords.clear();
    this.emotionLexicon.clear();
  }
}

export default SentimentAnalysisService;