/**
 * Collaboration Service Test Suite
 *
 * Tests for real-time collaboration features including WebSocket management,
 * operational transforms, field locking, and user presence.
 */

import { describe, test, expect, beforeEach, afterEach, vi } from 'vitest';
import { CollaborationService } from '../services/collaborationService';
import type { CollaborativeUser, FieldLock, OperationalTransform } from '../types';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;

  constructor(url: string) {
    this.url = url;

    // Simulate connection opening
    setTimeout(() => {
      this.readyState = MockWebSocket.OPEN;
      if (this.onopen) {
        this.onopen(new Event('open'));
      }
    }, 10);
  }

  send(data: string) {
    // Simulate sending data
  }

  close() {
    this.readyState = MockWebSocket.CLOSED;
    if (this.onclose) {
      this.onclose(new CloseEvent('close'));
    }
  }

  // Simulate receiving a message
  simulateMessage(data: any) {
    if (this.onmessage) {
      this.onmessage(new MessageEvent('message', {
        data: JSON.stringify(data),
      }));
    }
  }

  // Simulate connection error
  simulateError() {
    if (this.onerror) {
      this.onerror(new Event('error'));
    }
  }
}

// Replace global WebSocket with mock
global.WebSocket = MockWebSocket as any;

describe('CollaborationService', () => {
  let collaborationService: CollaborationService;
  let mockUser: CollaborativeUser;

  beforeEach(() => {
    collaborationService = new CollaborationService();
    mockUser = {
      id: 'user-123',
      name: 'Test User',
      color: '#1890ff',
      isOnline: true,
      lastSeen: new Date().toISOString(),
      permissions: [
        {
          resource: 'grades',
          action: 'write',
          scope: ['all'],
        },
      ],
    };

    vi.clearAllMocks();
  });

  afterEach(() => {
    collaborationService.cleanup();
    vi.restoreAllMocks();
  });

  describe('Initialization', () => {
    test('should initialize collaboration for grades', async () => {
      const connectSpy = vi.spyOn(collaborationService, 'initializeCollaboration');

      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);

      expect(connectSpy).toHaveBeenCalledWith('grades', 'class-123', mockUser);
    });

    test('should handle WebSocket connection', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('connected', (endpoint) => {
          expect(endpoint).toContain('ws://localhost:8000/ws/grades/class-123/');
          resolve();
        });

        collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      });
    });
  });

  describe('User Presence', () => {
    test('should send user presence on join', async () => {
      const messageSpy = vi.spyOn(collaborationService, 'sendUserPresence');

      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);

      // Wait for connection to establish
      await new Promise(resolve => setTimeout(resolve, 20));

      expect(messageSpy).toHaveBeenCalledWith('join');
    });

    test('should handle user join messages', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('user_joined', (user) => {
          expect(user.id).toBe('user-456');
          expect(user.name).toBe('Another User');
          resolve();
        });

        collaborationService.initializeCollaboration('grades', 'class-123', mockUser);

        // Simulate another user joining
        setTimeout(() => {
          const ws = (collaborationService as any).wsManager.connections.values().next().value;
          if (ws) {
            ws.simulateMessage({
              type: 'user_presence',
              payload: {
                action: 'join',
                user: {
                  id: 'user-456',
                  name: 'Another User',
                  color: '#52c41a',
                  isOnline: true,
                  lastSeen: new Date().toISOString(),
                },
              },
              timestamp: new Date().toISOString(),
              userId: 'user-456',
              messageId: 'msg-123',
            });
          }
        }, 15);
      });
    });

    test('should track online users', async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);

      // Wait for connection
      await new Promise(resolve => setTimeout(resolve, 20));

      // Simulate user joining
      const ws = (collaborationService as any).wsManager.connections.values().next().value;
      if (ws) {
        ws.simulateMessage({
          type: 'user_presence',
          payload: {
            action: 'join',
            user: {
              id: 'user-456',
              name: 'Another User',
              color: '#52c41a',
              isOnline: true,
              lastSeen: new Date().toISOString(),
            },
          },
          timestamp: new Date().toISOString(),
          userId: 'user-456',
          messageId: 'msg-123',
        });
      }

      const onlineUsers = collaborationService.getOnlineUsers();
      expect(onlineUsers).toHaveLength(1);
      expect(onlineUsers[0].id).toBe('user-456');
    });
  });

  describe('Field Locking', () => {
    beforeEach(async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    test('should request field lock successfully', async () => {
      const lockRequested = await collaborationService.requestFieldLock('points');
      expect(lockRequested).toBe(true);

      const locks = collaborationService.getFieldLocks();
      expect(locks.has('points')).toBe(true);

      const lock = locks.get('points');
      expect(lock?.userId).toBe(mockUser.id);
      expect(lock?.field).toBe('points');
    });

    test('should prevent locking already locked field', async () => {
      // First lock should succeed
      const firstLock = await collaborationService.requestFieldLock('comments');
      expect(firstLock).toBe(true);

      // Simulate another user trying to lock the same field
      const anotherUser: CollaborativeUser = {
        ...mockUser,
        id: 'user-456',
        name: 'Another User',
      };

      const anotherService = new CollaborationService();
      anotherService.initializeCollaboration('grades', 'class-123', anotherUser);
      await new Promise(resolve => setTimeout(resolve, 20));

      // Second lock should fail
      const secondLock = await anotherService.requestFieldLock('comments');
      expect(secondLock).toBe(false);

      anotherService.cleanup();
    });

    test('should release field lock', async () => {
      await collaborationService.requestFieldLock('points');

      let locks = collaborationService.getFieldLocks();
      expect(locks.has('points')).toBe(true);

      collaborationService.releaseFieldLock('points');

      locks = collaborationService.getFieldLocks();
      expect(locks.has('points')).toBe(false);
    });

    test('should auto-release expired locks', async () => {
      const lockDuration = 100; // 100ms for testing
      await collaborationService.requestFieldLock('points', lockDuration);

      let locks = collaborationService.getFieldLocks();
      expect(locks.has('points')).toBe(true);

      // Wait for lock to expire
      await new Promise(resolve => setTimeout(resolve, lockDuration + 50));

      locks = collaborationService.getFieldLocks();
      expect(locks.has('points')).toBe(false);
    });
  });

  describe('Operational Transforms', () => {
    beforeEach(async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    test('should send operational transform', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('message_sent', (message) => {
          expect(message.type).toBe('operational_transform');
          expect(message.payload.documentId).toBe('grade-matrix');
          resolve();
        });

        const transform: OperationalTransform = {
          id: 'op-123',
          type: 'replace',
          position: 0,
          length: 2,
          content: '85',
          timestamp: new Date().toISOString(),
          userId: mockUser.id,
          version: 1,
        };

        collaborationService.sendOperationalTransform('grade-matrix', transform, '90');
      });
    });

    test('should handle operational transform messages', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('operational_transform_received', (documentId, transforms, version, newState) => {
          expect(documentId).toBe('grade-matrix');
          expect(transforms).toHaveLength(1);
          expect(version).toBe(2);
          resolve();
        });

        const ws = (collaborationService as any).wsManager.connections.values().next().value;
        if (ws) {
          ws.simulateMessage({
            type: 'operational_transform',
            payload: {
              documentId: 'grade-matrix',
              transforms: [{
                id: 'op-456',
                type: 'insert',
                position: 5,
                length: 0,
                content: '5',
                timestamp: new Date().toISOString(),
                userId: 'user-456',
                version: 2,
              }],
              version: 2,
              newState: '90.5',
            },
            timestamp: new Date().toISOString(),
            userId: 'user-456',
            messageId: 'msg-456',
          });
        }
      });
    });
  });

  describe('Grade Updates', () => {
    beforeEach(async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    test('should send grade update', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('message_sent', (message) => {
          expect(message.type).toBe('grade_updated');
          expect(message.payload.studentId).toBe('student-123');
          expect(message.payload.assignmentId).toBe('assignment-456');
          expect(message.payload.value).toBe(85);
          resolve();
        });

        collaborationService.sendGradeUpdate('student-123', 'assignment-456', 85, 1);
      });
    });

    test('should handle grade update messages', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('grade_updated', (studentId, assignmentId, value, version) => {
          expect(studentId).toBe('student-789');
          expect(assignmentId).toBe('assignment-101');
          expect(value).toBe(92);
          expect(version).toBe(2);
          resolve();
        });

        const ws = (collaborationService as any).wsManager.connections.values().next().value;
        if (ws) {
          ws.simulateMessage({
            type: 'grade_updated',
            payload: {
              studentId: 'student-789',
              assignmentId: 'assignment-101',
              value: 92,
              version: 2,
            },
            timestamp: new Date().toISOString(),
            userId: 'user-456',
            messageId: 'msg-789',
          });
        }
      });
    });
  });

  describe('Change History', () => {
    beforeEach(async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));
    });

    test('should record grade changes in history', async () => {
      collaborationService.sendGradeUpdate('student-123', 'assignment-456', 85, 1);

      const history = collaborationService.getChangeHistory('student-123_assignment-456');
      expect(history).toHaveLength(1);

      const change = history[0];
      expect(change.resource).toBe('grade');
      expect(change.resourceId).toBe('student-123_assignment-456');
      expect(change.field).toBe('points');
      expect(change.newValue).toBe(85);
      expect(change.userId).toBe(mockUser.id);
    });

    test('should limit change history to 100 entries', async () => {
      // Add 150 changes
      for (let i = 0; i < 150; i++) {
        collaborationService.sendGradeUpdate('student-123', 'assignment-456', i, i + 1);
      }

      const history = collaborationService.getChangeHistory('student-123_assignment-456');
      expect(history).toHaveLength(100);

      // Should have the most recent changes
      expect(history[0].newValue).toBe(149);
      expect(history[99].newValue).toBe(50);
    });
  });

  describe('Error Handling', () => {
    test('should handle WebSocket connection errors', async () => {
      return new Promise<void>((resolve) => {
        collaborationService.on('error', (endpoint, error) => {
          expect(error).toBeInstanceOf(Event);
          resolve();
        });

        collaborationService.initializeCollaboration('grades', 'class-123', mockUser);

        // Wait for connection then simulate error
        setTimeout(() => {
          const ws = (collaborationService as any).wsManager.connections.values().next().value;
          if (ws) {
            ws.simulateError();
          }
        }, 15);
      });
    });

    test('should handle malformed messages gracefully', async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));

      // Should not throw when receiving malformed message
      const ws = (collaborationService as any).wsManager.connections.values().next().value;
      if (ws && ws.onmessage) {
        const malformedEvent = new MessageEvent('message', {
          data: 'invalid json',
        });

        // Should not throw
        expect(() => {
          ws.onmessage(malformedEvent);
        }).not.toThrow();
      }
    });
  });

  describe('Cleanup', () => {
    test('should cleanup resources properly', async () => {
      collaborationService.initializeCollaboration('grades', 'class-123', mockUser);
      await new Promise(resolve => setTimeout(resolve, 20));

      // Add some state
      await collaborationService.requestFieldLock('points');
      collaborationService.sendGradeUpdate('student-123', 'assignment-456', 85, 1);

      // Verify state exists
      expect(collaborationService.getFieldLocks().size).toBeGreaterThan(0);
      expect(collaborationService.getOnlineUsers()).toHaveLength(0); // Only tracked when messages received

      // Cleanup
      collaborationService.cleanup();

      // Verify cleanup
      expect(collaborationService.getFieldLocks().size).toBe(0);
      expect(collaborationService.getOnlineUsers()).toHaveLength(0);
    });
  });
});

// Integration tests
describe('Collaboration Integration', () => {
  test('should handle complete collaboration workflow', async () => {
    const user1: CollaborativeUser = {
      id: 'user-1',
      name: 'User One',
      color: '#1890ff',
      isOnline: true,
      lastSeen: new Date().toISOString(),
      permissions: [{ resource: 'grades', action: 'write', scope: ['all'] }],
    };

    const user2: CollaborativeUser = {
      id: 'user-2',
      name: 'User Two',
      color: '#52c41a',
      isOnline: true,
      lastSeen: new Date().toISOString(),
      permissions: [{ resource: 'grades', action: 'write', scope: ['all'] }],
    };

    const service1 = new CollaborationService();
    const service2 = new CollaborationService();

    try {
      // Initialize both services
      service1.initializeCollaboration('grades', 'class-123', user1);
      service2.initializeCollaboration('grades', 'class-123', user2);

      await new Promise(resolve => setTimeout(resolve, 30));

      // User 1 requests lock
      const lockSuccess = await service1.requestFieldLock('points');
      expect(lockSuccess).toBe(true);

      // User 2 tries to lock same field (should fail)
      const lockFail = await service2.requestFieldLock('points');
      expect(lockFail).toBe(false);

      // User 1 releases lock
      service1.releaseFieldLock('points');

      // User 2 can now lock
      const lockSuccess2 = await service2.requestFieldLock('points');
      expect(lockSuccess2).toBe(true);

      // User 2 updates grade
      service2.sendGradeUpdate('student-123', 'assignment-456', 95, 1);

      // Check change history
      const history = service2.getChangeHistory('student-123_assignment-456');
      expect(history).toHaveLength(1);
      expect(history[0].newValue).toBe(95);

    } finally {
      service1.cleanup();
      service2.cleanup();
    }
  });
});