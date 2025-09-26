/**
 * Real-time Communication Socket Manager
 *
 * Manages WebSocket connections for real-time features
 */

import { io, Socket } from 'socket.io-client';
import { Message, CommunicationChannel } from '../../types/innovation';

export interface SocketEvents {
  // Message events
  'message:new': (message: Message) => void;
  'message:read': (data: { messageId: string; userId: string; readAt: Date }) => void;
  'message:typing': (data: { channelId: string; userId: string; isTyping: boolean }) => void;

  // Channel events
  'channel:joined': (data: { channelId: string; userId: string }) => void;
  'channel:left': (data: { channelId: string; userId: string }) => void;
  'channel:updated': (channel: CommunicationChannel) => void;

  // Collaboration events
  'document:change': (data: { documentId: string; changes: any; userId: string }) => void;
  'document:cursor': (data: { documentId: string; userId: string; position: any }) => void;
  'document:lock': (data: { documentId: string; userId: string; section: string }) => void;

  // Video call events
  'call:incoming': (data: { callId: string; from: string; channelId?: string }) => void;
  'call:accepted': (data: { callId: string; userId: string }) => void;
  'call:rejected': (data: { callId: string; userId: string }) => void;
  'call:ended': (data: { callId: string; userId: string }) => void;

  // System events
  'system:notification': (data: { type: string; message: string; data?: any }) => void;
  'user:online': (data: { userId: string; status: 'online' | 'away' | 'busy' }) => void;
  'user:offline': (data: { userId: string }) => void;
}

class SocketManager {
  private socket: Socket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private eventListeners: Map<string, Set<Function>> = new Map();
  private connectionState: 'disconnected' | 'connecting' | 'connected' | 'error' = 'disconnected';

  constructor() {
    this.setupSocket();
  }

  private setupSocket() {
    const serverUrl = import.meta.env.VITE_SOCKET_URL || 'http://localhost:8000';

    this.socket = io(serverUrl, {
      autoConnect: false,
      timeout: 20000,
      auth: {
        token: this.getAuthToken(),
      },
    });

    this.setupEventHandlers();
  }

  private setupEventHandlers() {
    if (!this.socket) return;

    this.socket.on('connect', () => {
      console.log('Socket connected');
      this.connectionState = 'connected';
      this.reconnectAttempts = 0;
      this.emit('connection:established');
    });

    this.socket.on('disconnect', (reason) => {
      console.log('Socket disconnected:', reason);
      this.connectionState = 'disconnected';
      this.emit('connection:lost', reason);

      if (reason === 'io server disconnect') {
        // Server disconnected us, try to reconnect
        this.handleReconnect();
      }
    });

    this.socket.on('connect_error', (error) => {
      console.error('Socket connection error:', error);
      this.connectionState = 'error';
      this.emit('connection:error', error);
      this.handleReconnect();
    });

    // Setup specific event handlers
    this.setupMessageHandlers();
    this.setupChannelHandlers();
    this.setupCollaborationHandlers();
    this.setupCallHandlers();
    this.setupSystemHandlers();
  }

  private setupMessageHandlers() {
    if (!this.socket) return;

    this.socket.on('message:new', (message: Message) => {
      this.emit('message:new', message);
    });

    this.socket.on('message:read', (data) => {
      this.emit('message:read', data);
    });

    this.socket.on('message:typing', (data) => {
      this.emit('message:typing', data);
    });
  }

  private setupChannelHandlers() {
    if (!this.socket) return;

    this.socket.on('channel:joined', (data) => {
      this.emit('channel:joined', data);
    });

    this.socket.on('channel:left', (data) => {
      this.emit('channel:left', data);
    });

    this.socket.on('channel:updated', (channel) => {
      this.emit('channel:updated', channel);
    });
  }

  private setupCollaborationHandlers() {
    if (!this.socket) return;

    this.socket.on('document:change', (data) => {
      this.emit('document:change', data);
    });

    this.socket.on('document:cursor', (data) => {
      this.emit('document:cursor', data);
    });

    this.socket.on('document:lock', (data) => {
      this.emit('document:lock', data);
    });
  }

  private setupCallHandlers() {
    if (!this.socket) return;

    this.socket.on('call:incoming', (data) => {
      this.emit('call:incoming', data);
    });

    this.socket.on('call:accepted', (data) => {
      this.emit('call:accepted', data);
    });

    this.socket.on('call:rejected', (data) => {
      this.emit('call:rejected', data);
    });

    this.socket.on('call:ended', (data) => {
      this.emit('call:ended', data);
    });
  }

  private setupSystemHandlers() {
    if (!this.socket) return;

    this.socket.on('system:notification', (data) => {
      this.emit('system:notification', data);
    });

    this.socket.on('user:online', (data) => {
      this.emit('user:online', data);
    });

    this.socket.on('user:offline', (data) => {
      this.emit('user:offline', data);
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts >= this.maxReconnectAttempts) {
      console.error('Max reconnection attempts reached');
      this.emit('connection:failed');
      return;
    }

    this.reconnectAttempts++;
    const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);

    console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms`);

    setTimeout(() => {
      if (this.socket) {
        this.connectionState = 'connecting';
        this.socket.connect();
      }
    }, delay);
  }

  private getAuthToken(): string | null {
    // Get token from localStorage or other secure storage
    return localStorage.getItem('authToken');
  }

  // Public API
  connect(token?: string) {
    if (token) {
      localStorage.setItem('authToken', token);
      if (this.socket) {
        this.socket.auth = { token };
      }
    }

    if (this.socket && this.connectionState === 'disconnected') {
      this.connectionState = 'connecting';
      this.socket.connect();
    }
  }

  disconnect() {
    if (this.socket) {
      this.socket.disconnect();
      this.connectionState = 'disconnected';
    }
  }

  // Event management
  on<K extends keyof SocketEvents>(event: K, callback: SocketEvents[K]): void;
  on(event: string, callback: Function): void;
  on(event: string, callback: Function): void {
    if (!this.eventListeners.has(event)) {
      this.eventListeners.set(event, new Set());
    }
    this.eventListeners.get(event)!.add(callback);
  }

  off(event: string, callback?: Function): void {
    if (callback) {
      this.eventListeners.get(event)?.delete(callback);
    } else {
      this.eventListeners.delete(event);
    }
  }

  private emit(event: string, ...args: any[]): void {
    const listeners = this.eventListeners.get(event);
    if (listeners) {
      listeners.forEach(callback => {
        try {
          callback(...args);
        } catch (error) {
          console.error(`Error in socket event handler for ${event}:`, error);
        }
      });
    }
  }

  // Message operations
  sendMessage(message: Omit<Message, 'id' | 'timestamp'>): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('message:send', message);
    } else {
      console.warn('Cannot send message: socket not connected');
    }
  }

  markMessageRead(messageId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('message:mark_read', { messageId });
    }
  }

  setTyping(channelId: string, isTyping: boolean): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('message:typing', { channelId, isTyping });
    }
  }

  // Channel operations
  joinChannel(channelId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('channel:join', { channelId });
    }
  }

  leaveChannel(channelId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('channel:leave', { channelId });
    }
  }

  // Collaboration operations
  sendDocumentChange(documentId: string, changes: any): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('document:change', { documentId, changes });
    }
  }

  sendCursorPosition(documentId: string, position: any): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('document:cursor', { documentId, position });
    }
  }

  lockDocumentSection(documentId: string, section: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('document:lock', { documentId, section });
    }
  }

  unlockDocumentSection(documentId: string, section: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('document:unlock', { documentId, section });
    }
  }

  // Video call operations
  initiateCall(recipientIds: string[], channelId?: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('call:initiate', { recipientIds, channelId });
    }
  }

  acceptCall(callId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('call:accept', { callId });
    }
  }

  rejectCall(callId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('call:reject', { callId });
    }
  }

  endCall(callId: string): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('call:end', { callId });
    }
  }

  // Status management
  updateUserStatus(status: 'online' | 'away' | 'busy'): void {
    if (this.socket && this.connectionState === 'connected') {
      this.socket.emit('user:status', { status });
    }
  }

  // Utility methods
  isConnected(): boolean {
    return this.connectionState === 'connected';
  }

  getConnectionState(): string {
    return this.connectionState;
  }

  // Cleanup
  destroy(): void {
    if (this.socket) {
      this.socket.disconnect();
      this.socket.removeAllListeners();
    }
    this.eventListeners.clear();
    this.connectionState = 'disconnected';
  }
}

// Create singleton instance
export const socketManager = new SocketManager();

// React hook for socket management
export const useSocket = () => {
  return {
    socket: socketManager,
    connect: socketManager.connect.bind(socketManager),
    disconnect: socketManager.disconnect.bind(socketManager),
    isConnected: socketManager.isConnected.bind(socketManager),
    on: socketManager.on.bind(socketManager),
    off: socketManager.off.bind(socketManager),
  };
};

export default socketManager;