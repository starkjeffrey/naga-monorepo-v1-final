/**
 * Student WebSocket Service
 *
 * Real-time communication service for student updates:
 * - Student data change notifications
 * - Enrollment status updates
 * - Alert notifications
 * - Collaborative editing support
 * - Connection management
 */

import { EventEmitter } from 'events';
import type { Student, StudentEvent } from '../types/Student';

interface WebSocketMessage {
  type: string;
  payload: any;
  timestamp: string;
  id: string;
}

interface StudentWebSocketConfig {
  reconnectInterval?: number;
  maxReconnectAttempts?: number;
  heartbeatInterval?: number;
  enableHeartbeat?: boolean;
}

class StudentWebSocketService extends EventEmitter {
  private ws: WebSocket | null = null;
  private url: string;
  private config: StudentWebSocketConfig;
  private reconnectAttempts = 0;
  private reconnectTimer: NodeJS.Timeout | null = null;
  private heartbeatTimer: NodeJS.Timeout | null = null;
  private isConnecting = false;
  private isConnected = false;
  private subscribedChannels = new Set<string>();

  constructor(config: StudentWebSocketConfig = {}) {
    super();
    this.config = {
      reconnectInterval: 3000,
      maxReconnectAttempts: 5,
      heartbeatInterval: 30000,
      enableHeartbeat: true,
      ...config,
    };

    // Construct WebSocket URL
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    this.url = `${protocol}//${host}/ws/students/`;
  }

  /**
   * Connect to WebSocket
   */
  connect(): Promise<void> {
    if (this.isConnecting || this.isConnected) {
      return Promise.resolve();
    }

    return new Promise((resolve, reject) => {
      this.isConnecting = true;

      try {
        this.ws = new WebSocket(this.url);

        this.ws.onopen = () => {
          this.isConnecting = false;
          this.isConnected = true;
          this.reconnectAttempts = 0;

          this.emit('connected');
          this.startHeartbeat();
          this.resubscribeToChannels();

          resolve();
        };

        this.ws.onmessage = (event) => {
          this.handleMessage(event);
        };

        this.ws.onclose = (event) => {
          this.isConnecting = false;
          this.isConnected = false;
          this.stopHeartbeat();

          this.emit('disconnected', { code: event.code, reason: event.reason });

          // Attempt reconnection if not intentionally closed
          if (event.code !== 1000 && this.reconnectAttempts < this.config.maxReconnectAttempts!) {
            this.scheduleReconnect();
          }
        };

        this.ws.onerror = (error) => {
          this.isConnecting = false;
          this.emit('error', error);

          if (this.reconnectAttempts === 0) {
            reject(error);
          }
        };

      } catch (error) {
        this.isConnecting = false;
        reject(error);
      }
    });
  }

  /**
   * Disconnect from WebSocket
   */
  disconnect(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }

    this.stopHeartbeat();

    if (this.ws) {
      this.ws.close(1000, 'Client disconnect');
      this.ws = null;
    }

    this.isConnected = false;
    this.subscribedChannels.clear();
  }

  /**
   * Subscribe to student updates
   */
  subscribeToStudent(studentId: string): void {
    const channel = `student.${studentId}`;
    this.subscribe(channel);
  }

  /**
   * Unsubscribe from student updates
   */
  unsubscribeFromStudent(studentId: string): void {
    const channel = `student.${studentId}`;
    this.unsubscribe(channel);
  }

  /**
   * Subscribe to all student updates
   */
  subscribeToAllStudents(): void {
    this.subscribe('students.all');
  }

  /**
   * Subscribe to enrollment updates
   */
  subscribeToEnrollments(studentId?: string): void {
    const channel = studentId ? `enrollments.student.${studentId}` : 'enrollments.all';
    this.subscribe(channel);
  }

  /**
   * Subscribe to alert notifications
   */
  subscribeToAlerts(studentId?: string): void {
    const channel = studentId ? `alerts.student.${studentId}` : 'alerts.all';
    this.subscribe(channel);
  }

  /**
   * Subscribe to bulk operation updates
   */
  subscribeToBulkOperations(): void {
    this.subscribe('bulk_operations');
  }

  /**
   * Generic subscribe method
   */
  private subscribe(channel: string): void {
    if (this.subscribedChannels.has(channel)) {
      return;
    }

    this.subscribedChannels.add(channel);

    if (this.isConnected) {
      this.send({
        type: 'subscribe',
        payload: { channel },
        timestamp: new Date().toISOString(),
        id: this.generateId(),
      });
    }
  }

  /**
   * Generic unsubscribe method
   */
  private unsubscribe(channel: string): void {
    if (!this.subscribedChannels.has(channel)) {
      return;
    }

    this.subscribedChannels.delete(channel);

    if (this.isConnected) {
      this.send({
        type: 'unsubscribe',
        payload: { channel },
        timestamp: new Date().toISOString(),
        id: this.generateId(),
      });
    }
  }

  /**
   * Send message to server
   */
  private send(message: WebSocketMessage): void {
    if (this.ws && this.isConnected) {
      this.ws.send(JSON.stringify(message));
    }
  }

  /**
   * Handle incoming messages
   */
  private handleMessage(event: MessageEvent): void {
    try {
      const message: WebSocketMessage = JSON.parse(event.data);

      switch (message.type) {
        case 'student.updated':
          this.handleStudentUpdated(message.payload);
          break;

        case 'student.created':
          this.handleStudentCreated(message.payload);
          break;

        case 'student.deleted':
          this.handleStudentDeleted(message.payload);
          break;

        case 'enrollment.updated':
          this.handleEnrollmentUpdated(message.payload);
          break;

        case 'enrollment.created':
          this.handleEnrollmentCreated(message.payload);
          break;

        case 'enrollment.deleted':
          this.handleEnrollmentDeleted(message.payload);
          break;

        case 'alert.created':
          this.handleAlertCreated(message.payload);
          break;

        case 'alert.cleared':
          this.handleAlertCleared(message.payload);
          break;

        case 'bulk_operation.progress':
          this.handleBulkOperationProgress(message.payload);
          break;

        case 'bulk_operation.completed':
          this.handleBulkOperationCompleted(message.payload);
          break;

        case 'pong':
          // Heartbeat response - no action needed
          break;

        case 'error':
          this.emit('error', new Error(message.payload.message));
          break;

        default:
          console.warn('Unknown WebSocket message type:', message.type);
      }

    } catch (error) {
      console.error('Failed to parse WebSocket message:', error);
    }
  }

  /**
   * Handle student updated event
   */
  private handleStudentUpdated(payload: {
    student: Student;
    changes: Array<{ field: string; oldValue: any; newValue: any }>;
    updatedBy: string;
  }): void {
    this.emit('student:updated', payload);
    this.emit(`student:${payload.student.id}:updated`, payload);
  }

  /**
   * Handle student created event
   */
  private handleStudentCreated(payload: { student: Student; createdBy: string }): void {
    this.emit('student:created', payload);
  }

  /**
   * Handle student deleted event
   */
  private handleStudentDeleted(payload: { studentId: string; deletedBy: string }): void {
    this.emit('student:deleted', payload);
    this.emit(`student:${payload.studentId}:deleted`, payload);
  }

  /**
   * Handle enrollment updated event
   */
  private handleEnrollmentUpdated(payload: any): void {
    this.emit('enrollment:updated', payload);
    this.emit(`student:${payload.studentId}:enrollment:updated`, payload);
  }

  /**
   * Handle enrollment created event
   */
  private handleEnrollmentCreated(payload: any): void {
    this.emit('enrollment:created', payload);
    this.emit(`student:${payload.studentId}:enrollment:created`, payload);
  }

  /**
   * Handle enrollment deleted event
   */
  private handleEnrollmentDeleted(payload: any): void {
    this.emit('enrollment:deleted', payload);
    this.emit(`student:${payload.studentId}:enrollment:deleted`, payload);
  }

  /**
   * Handle alert created event
   */
  private handleAlertCreated(payload: { studentId: string; alert: any }): void {
    this.emit('alert:created', payload);
    this.emit(`student:${payload.studentId}:alert:created`, payload);
  }

  /**
   * Handle alert cleared event
   */
  private handleAlertCleared(payload: { studentId: string; alertId: string }): void {
    this.emit('alert:cleared', payload);
    this.emit(`student:${payload.studentId}:alert:cleared`, payload);
  }

  /**
   * Handle bulk operation progress event
   */
  private handleBulkOperationProgress(payload: {
    operationId: string;
    progress: number;
    status: string;
    processedCount: number;
    totalCount: number;
  }): void {
    this.emit('bulkOperation:progress', payload);
    this.emit(`bulkOperation:${payload.operationId}:progress`, payload);
  }

  /**
   * Handle bulk operation completed event
   */
  private handleBulkOperationCompleted(payload: {
    operationId: string;
    result: any;
    completedAt: string;
  }): void {
    this.emit('bulkOperation:completed', payload);
    this.emit(`bulkOperation:${payload.operationId}:completed`, payload);
  }

  /**
   * Schedule reconnection attempt
   */
  private scheduleReconnect(): void {
    if (this.reconnectTimer) {
      return;
    }

    this.reconnectAttempts++;
    const delay = this.config.reconnectInterval! * Math.pow(2, this.reconnectAttempts - 1);

    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      this.connect().catch(() => {
        // Will trigger another reconnect attempt if limit not reached
      });
    }, delay);

    this.emit('reconnecting', { attempt: this.reconnectAttempts, delay });
  }

  /**
   * Start heartbeat to keep connection alive
   */
  private startHeartbeat(): void {
    if (!this.config.enableHeartbeat) {
      return;
    }

    this.heartbeatTimer = setInterval(() => {
      if (this.isConnected) {
        this.send({
          type: 'ping',
          payload: {},
          timestamp: new Date().toISOString(),
          id: this.generateId(),
        });
      }
    }, this.config.heartbeatInterval!);
  }

  /**
   * Stop heartbeat
   */
  private stopHeartbeat(): void {
    if (this.heartbeatTimer) {
      clearInterval(this.heartbeatTimer);
      this.heartbeatTimer = null;
    }
  }

  /**
   * Resubscribe to all channels after reconnection
   */
  private resubscribeToChannels(): void {
    for (const channel of this.subscribedChannels) {
      this.send({
        type: 'subscribe',
        payload: { channel },
        timestamp: new Date().toISOString(),
        id: this.generateId(),
      });
    }
  }

  /**
   * Generate unique message ID
   */
  private generateId(): string {
    return `${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get connection status
   */
  getConnectionStatus(): {
    isConnected: boolean;
    isConnecting: boolean;
    reconnectAttempts: number;
    subscribedChannels: string[];
  } {
    return {
      isConnected: this.isConnected,
      isConnecting: this.isConnecting,
      reconnectAttempts: this.reconnectAttempts,
      subscribedChannels: Array.from(this.subscribedChannels),
    };
  }

  /**
   * Force reconnection
   */
  forceReconnect(): void {
    this.disconnect();
    this.connect();
  }
}

// Export singleton instance
export const studentWebSocketService = new StudentWebSocketService();
export default studentWebSocketService;