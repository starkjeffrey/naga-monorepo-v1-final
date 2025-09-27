/**
 * Real-Time Collaboration Service
 *
 * Handles WebSocket connections, operational transforms, and real-time synchronization
 * for academic management features including grades, enrollment, and scheduling.
 */

import { EventEmitter } from 'events';
import type {
  CollaborativeUser,
  FieldLock,
  ChangeHistory,
  OperationalTransform,
  WebSocketMessage,
  GradeUpdateMessage,
  UserPresenceMessage,
  FieldLockMessage,
  ConflictMessage,
} from '../types';

// ============================================================================
// WebSocket Connection Manager
// ============================================================================

class WebSocketManager extends EventEmitter {
  private connections = new Map<string, WebSocket>();
  private reconnectAttempts = new Map<string, number>();
  private maxReconnectAttempts = 5;
  private reconnectDelay = 3000;

  /**
   * Connect to a WebSocket endpoint
   */
  connect(endpoint: string, options: {
    onOpen?: () => void;
    onMessage?: (data: any) => void;
    onClose?: () => void;
    onError?: (error: Event) => void;
  } = {}): WebSocket {
    if (this.connections.has(endpoint)) {
      return this.connections.get(endpoint)!;
    }

    const ws = new WebSocket(endpoint);
    this.connections.set(endpoint, ws);

    ws.onopen = () => {
      console.log(`Connected to ${endpoint}`);
      this.reconnectAttempts.delete(endpoint);
      options.onOpen?.();
      this.emit('connected', endpoint);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        options.onMessage?.(data);
        this.emit('message', endpoint, data);
      } catch (error) {
        console.error('Failed to parse WebSocket message:', error);
      }
    };

    ws.onclose = () => {
      console.log(`Disconnected from ${endpoint}`);
      this.connections.delete(endpoint);
      options.onClose?.();
      this.emit('disconnected', endpoint);
      this.attemptReconnect(endpoint, options);
    };

    ws.onerror = (error) => {
      console.error(`WebSocket error for ${endpoint}:`, error);
      options.onError?.(error);
      this.emit('error', endpoint, error);
    };

    return ws;
  }

  /**
   * Attempt to reconnect to a WebSocket endpoint
   */
  private attemptReconnect(endpoint: string, options: any) {
    const attempts = this.reconnectAttempts.get(endpoint) || 0;

    if (attempts < this.maxReconnectAttempts) {
      this.reconnectAttempts.set(endpoint, attempts + 1);

      setTimeout(() => {
        console.log(`Attempting to reconnect to ${endpoint} (attempt ${attempts + 1})`);
        this.connect(endpoint, options);
      }, this.reconnectDelay * Math.pow(2, attempts)); // Exponential backoff
    } else {
      console.error(`Max reconnection attempts reached for ${endpoint}`);
      this.emit('reconnect_failed', endpoint);
    }
  }

  /**
   * Send message to a WebSocket connection
   */
  send(endpoint: string, message: any): boolean {
    const ws = this.connections.get(endpoint);
    if (ws && ws.readyState === WebSocket.OPEN) {
      try {
        ws.send(JSON.stringify(message));
        return true;
      } catch (error) {
        console.error('Failed to send WebSocket message:', error);
        return false;
      }
    }
    return false;
  }

  /**
   * Disconnect from a WebSocket endpoint
   */
  disconnect(endpoint: string): void {
    const ws = this.connections.get(endpoint);
    if (ws) {
      ws.close();
      this.connections.delete(endpoint);
    }
  }

  /**
   * Disconnect from all WebSocket connections
   */
  disconnectAll(): void {
    this.connections.forEach((ws, endpoint) => {
      ws.close();
    });
    this.connections.clear();
    this.reconnectAttempts.clear();
  }

  /**
   * Get connection status
   */
  getConnectionStatus(endpoint: string): 'connecting' | 'open' | 'closing' | 'closed' {
    const ws = this.connections.get(endpoint);
    if (!ws) return 'closed';

    switch (ws.readyState) {
      case WebSocket.CONNECTING: return 'connecting';
      case WebSocket.OPEN: return 'open';
      case WebSocket.CLOSING: return 'closing';
      case WebSocket.CLOSED: return 'closed';
      default: return 'closed';
    }
  }
}

// ============================================================================
// Operational Transform Engine
// ============================================================================

class OperationalTransformEngine {
  private transforms = new Map<string, OperationalTransform[]>();
  private version = new Map<string, number>();

  /**
   * Apply operational transform
   */
  applyTransform(
    documentId: string,
    transform: OperationalTransform,
    currentState: any
  ): { newState: any; transformedOperations: OperationalTransform[] } {
    const documentTransforms = this.transforms.get(documentId) || [];
    const currentVersion = this.version.get(documentId) || 0;

    // Transform the operation against concurrent operations
    const transformedOperations = this.transformAgainstConcurrent(
      transform,
      documentTransforms.filter(t => t.version > transform.version)
    );

    // Apply the transformed operations to the current state
    let newState = { ...currentState };
    transformedOperations.forEach(op => {
      newState = this.applyOperation(newState, op);
    });

    // Store the transform
    documentTransforms.push(...transformedOperations);
    this.transforms.set(documentId, documentTransforms);
    this.version.set(documentId, currentVersion + 1);

    return { newState, transformedOperations };
  }

  /**
   * Transform operation against concurrent operations
   */
  private transformAgainstConcurrent(
    operation: OperationalTransform,
    concurrentOps: OperationalTransform[]
  ): OperationalTransform[] => {
    let transformedOp = { ...operation };
    const result: OperationalTransform[] = [];

    concurrentOps.forEach(concurrentOp => {
      transformedOp = this.transformOperationPair(transformedOp, concurrentOp);
    });

    result.push(transformedOp);
    return result;
  }

  /**
   * Transform two operations against each other
   */
  private transformOperationPair(
    op1: OperationalTransform,
    op2: OperationalTransform
  ): OperationalTransform {
    // Simplified operational transform logic
    // In a real implementation, this would handle all cases comprehensively

    switch (op1.type) {
      case 'insert':
        if (op2.type === 'insert') {
          if (op1.position <= op2.position) {
            return { ...op1 };
          } else {
            return { ...op1, position: op1.position + op2.length };
          }
        } else if (op2.type === 'delete') {
          if (op1.position <= op2.position) {
            return { ...op1 };
          } else if (op1.position > op2.position + op2.length) {
            return { ...op1, position: op1.position - op2.length };
          } else {
            return { ...op1, position: op2.position };
          }
        }
        break;

      case 'delete':
        if (op2.type === 'insert') {
          if (op1.position < op2.position) {
            return { ...op1 };
          } else {
            return { ...op1, position: op1.position + op2.length };
          }
        } else if (op2.type === 'delete') {
          if (op1.position + op1.length <= op2.position) {
            return { ...op1 };
          } else if (op1.position >= op2.position + op2.length) {
            return { ...op1, position: op1.position - op2.length };
          } else {
            // Overlapping deletes - merge them
            const newPosition = Math.min(op1.position, op2.position);
            const newLength = Math.max(
              op1.position + op1.length,
              op2.position + op2.length
            ) - newPosition;
            return { ...op1, position: newPosition, length: newLength };
          }
        }
        break;

      case 'replace':
        // Handle replace operations
        return { ...op1 };

      default:
        return { ...op1 };
    }

    return { ...op1 };
  }

  /**
   * Apply a single operation to state
   */
  private applyOperation(state: any, operation: OperationalTransform): any {
    switch (operation.type) {
      case 'insert':
        // Insert content at position
        if (typeof state === 'string') {
          return (
            state.substring(0, operation.position) +
            operation.content +
            state.substring(operation.position)
          );
        }
        break;

      case 'delete':
        // Delete content from position
        if (typeof state === 'string') {
          return (
            state.substring(0, operation.position) +
            state.substring(operation.position + operation.length)
          );
        }
        break;

      case 'replace':
        // Replace content at position
        if (typeof state === 'string') {
          return (
            state.substring(0, operation.position) +
            operation.content +
            state.substring(operation.position + operation.length)
          );
        }
        break;

      case 'retain':
        // No change needed for retain operations
        return state;

      default:
        return state;
    }

    return state;
  }

  /**
   * Get document version
   */
  getVersion(documentId: string): number {
    return this.version.get(documentId) || 0;
  }

  /**
   * Clear document history (for cleanup)
   */
  clearDocument(documentId: string): void {
    this.transforms.delete(documentId);
    this.version.delete(documentId);
  }
}

// ============================================================================
// Collaboration Service
// ============================================================================

export class CollaborationService extends EventEmitter {
  private wsManager = new WebSocketManager();
  private otEngine = new OperationalTransformEngine();
  private users = new Map<string, CollaborativeUser>();
  private fieldLocks = new Map<string, FieldLock>();
  private changeHistory = new Map<string, ChangeHistory[]>();
  private currentUser: CollaborativeUser | null = null;

  constructor() {
    super();
    this.setupEventHandlers();
  }

  /**
   * Initialize collaboration for a specific resource
   */
  initializeCollaboration(
    resourceType: 'grades' | 'enrollment' | 'schedule',
    resourceId: string,
    user: CollaborativeUser
  ): void {
    this.currentUser = user;
    const endpoint = `ws://localhost:8000/ws/${resourceType}/${resourceId}/`;

    this.wsManager.connect(endpoint, {
      onOpen: () => {
        this.sendUserPresence('join');
      },
      onMessage: (data) => {
        this.handleMessage(data);
      },
      onClose: () => {
        this.emit('disconnected', resourceType, resourceId);
      },
      onError: (error) => {
        this.emit('error', error);
      },
    });
  }

  /**
   * Send user presence update
   */
  sendUserPresence(action: 'join' | 'leave' | 'move', location?: string): void {
    if (!this.currentUser) return;

    const message: UserPresenceMessage = {
      type: 'user_presence',
      payload: {
        action,
        user: { ...this.currentUser, currentView: location },
        location,
      },
      timestamp: new Date().toISOString(),
      userId: this.currentUser.id,
      messageId: this.generateMessageId(),
    };

    this.broadcastMessage(message);
  }

  /**
   * Request field lock
   */
  requestFieldLock(field: string, expiresIn: number = 30000): Promise<boolean> {
    return new Promise((resolve) => {
      if (!this.currentUser) {
        resolve(false);
        return;
      }

      const lockId = `${field}_${this.currentUser.id}`;
      const existingLock = this.fieldLocks.get(field);

      // Check if field is already locked by another user
      if (existingLock && existingLock.userId !== this.currentUser.id) {
        resolve(false);
        return;
      }

      const lock: FieldLock = {
        field,
        userId: this.currentUser.id,
        userName: this.currentUser.name,
        timestamp: new Date().toISOString(),
        expiresAt: new Date(Date.now() + expiresIn).toISOString(),
      };

      this.fieldLocks.set(field, lock);

      const message: FieldLockMessage = {
        type: 'field_lock',
        payload: { field, lock },
        timestamp: new Date().toISOString(),
        userId: this.currentUser.id,
        messageId: this.generateMessageId(),
      };

      this.broadcastMessage(message);

      // Auto-release lock after expiration
      setTimeout(() => {
        this.releaseFieldLock(field);
      }, expiresIn);

      resolve(true);
    });
  }

  /**
   * Release field lock
   */
  releaseFieldLock(field: string): void {
    if (!this.currentUser) return;

    const lock = this.fieldLocks.get(field);
    if (lock && lock.userId === this.currentUser.id) {
      this.fieldLocks.delete(field);

      const message: FieldLockMessage = {
        type: 'field_unlock',
        payload: { field },
        timestamp: new Date().toISOString(),
        userId: this.currentUser.id,
        messageId: this.generateMessageId(),
      };

      this.broadcastMessage(message);
    }
  }

  /**
   * Send operational transform
   */
  sendOperationalTransform(
    documentId: string,
    transform: OperationalTransform,
    currentState: any
  ): void {
    const { newState, transformedOperations } = this.otEngine.applyTransform(
      documentId,
      transform,
      currentState
    );

    const message: WebSocketMessage = {
      type: 'operational_transform',
      payload: {
        documentId,
        transforms: transformedOperations,
        version: this.otEngine.getVersion(documentId),
        newState,
      },
      timestamp: new Date().toISOString(),
      userId: this.currentUser?.id || 'anonymous',
      messageId: this.generateMessageId(),
    };

    this.broadcastMessage(message);
    this.emit('state_updated', documentId, newState);
  }

  /**
   * Send grade update
   */
  sendGradeUpdate(
    studentId: string,
    assignmentId: string,
    value: number | null,
    version: number
  ): void {
    if (!this.currentUser) return;

    const message: GradeUpdateMessage = {
      type: 'grade_updated',
      payload: { studentId, assignmentId, value, version },
      timestamp: new Date().toISOString(),
      userId: this.currentUser.id,
      messageId: this.generateMessageId(),
    };

    this.broadcastMessage(message);
    this.addToChangeHistory('grade', `${studentId}_${assignmentId}`, 'points', null, value);
  }

  /**
   * Add change to history
   */
  private addToChangeHistory(
    resource: string,
    resourceId: string,
    field: string,
    oldValue: any,
    newValue: any
  ): void {
    if (!this.currentUser) return;

    const change: ChangeHistory = {
      id: this.generateMessageId(),
      resource,
      resourceId,
      field,
      oldValue,
      newValue,
      timestamp: new Date().toISOString(),
      userId: this.currentUser.id,
      userName: this.currentUser.name,
      operation: 'update',
    };

    const history = this.changeHistory.get(resourceId) || [];
    history.unshift(change);

    // Keep only last 100 changes
    if (history.length > 100) {
      history.splice(100);
    }

    this.changeHistory.set(resourceId, history);
    this.emit('change_recorded', change);
  }

  /**
   * Get change history for a resource
   */
  getChangeHistory(resourceId: string): ChangeHistory[] {
    return this.changeHistory.get(resourceId) || [];
  }

  /**
   * Handle incoming WebSocket messages
   */
  private handleMessage(data: WebSocketMessage): void {
    switch (data.type) {
      case 'user_presence':
        this.handleUserPresence(data as UserPresenceMessage);
        break;

      case 'field_lock':
      case 'field_unlock':
        this.handleFieldLock(data as FieldLockMessage);
        break;

      case 'grade_updated':
        this.handleGradeUpdate(data as GradeUpdateMessage);
        break;

      case 'operational_transform':
        this.handleOperationalTransform(data);
        break;

      case 'conflict_detected':
      case 'conflict_resolved':
        this.handleConflict(data as ConflictMessage);
        break;

      default:
        console.log('Unknown message type:', data.type);
    }
  }

  /**
   * Handle user presence messages
   */
  private handleUserPresence(message: UserPresenceMessage): void {
    const { action, user } = message.payload;

    switch (action) {
      case 'join':
        this.users.set(user.id, { ...user, isOnline: true });
        this.emit('user_joined', user);
        break;

      case 'leave':
        const existingUser = this.users.get(user.id);
        if (existingUser) {
          this.users.set(user.id, { ...existingUser, isOnline: false });
        }
        this.emit('user_left', user);
        break;

      case 'move':
        const currentUser = this.users.get(user.id);
        if (currentUser) {
          this.users.set(user.id, { ...currentUser, currentView: message.payload.location });
        }
        this.emit('user_moved', user, message.payload.location);
        break;
    }
  }

  /**
   * Handle field lock messages
   */
  private handleFieldLock(message: FieldLockMessage): void {
    const { field, lock } = message.payload;

    if (message.type === 'field_lock' && lock) {
      this.fieldLocks.set(field, lock);
      this.emit('field_locked', field, lock);
    } else if (message.type === 'field_unlock') {
      this.fieldLocks.delete(field);
      this.emit('field_unlocked', field);
    }
  }

  /**
   * Handle grade update messages
   */
  private handleGradeUpdate(message: GradeUpdateMessage): void {
    const { studentId, assignmentId, value, version } = message.payload;
    this.emit('grade_updated', studentId, assignmentId, value, version);
  }

  /**
   * Handle operational transform messages
   */
  private handleOperationalTransform(message: WebSocketMessage): void {
    const { documentId, transforms, version, newState } = message.payload;
    this.emit('operational_transform_received', documentId, transforms, version, newState);
  }

  /**
   * Handle conflict messages
   */
  private handleConflict(message: ConflictMessage): void {
    const { conflictId, description, resolution } = message.payload;

    if (message.type === 'conflict_detected') {
      this.emit('conflict_detected', conflictId, description);
    } else {
      this.emit('conflict_resolved', conflictId, resolution);
    }
  }

  /**
   * Broadcast message to WebSocket
   */
  private broadcastMessage(message: WebSocketMessage): void {
    // In a real implementation, you would send to the appropriate WebSocket endpoint
    // For now, we'll just emit the event
    this.emit('message_sent', message);
  }

  /**
   * Setup event handlers
   */
  private setupEventHandlers(): void {
    this.wsManager.on('connected', (endpoint) => {
      this.emit('connected', endpoint);
    });

    this.wsManager.on('disconnected', (endpoint) => {
      this.emit('disconnected', endpoint);
    });

    this.wsManager.on('error', (endpoint, error) => {
      this.emit('error', endpoint, error);
    });
  }

  /**
   * Generate unique message ID
   */
  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * Get current online users
   */
  getOnlineUsers(): CollaborativeUser[] {
    return Array.from(this.users.values()).filter(user => user.isOnline);
  }

  /**
   * Get field locks
   */
  getFieldLocks(): Map<string, FieldLock> {
    return new Map(this.fieldLocks);
  }

  /**
   * Cleanup resources
   */
  cleanup(): void {
    if (this.currentUser) {
      this.sendUserPresence('leave');
    }

    this.wsManager.disconnectAll();
    this.users.clear();
    this.fieldLocks.clear();
    this.changeHistory.clear();
    this.removeAllListeners();
  }
}

// ============================================================================
// Singleton instance
// ============================================================================

export const collaborationService = new CollaborationService();