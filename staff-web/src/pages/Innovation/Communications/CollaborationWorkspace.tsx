/**
 * CollaborationWorkspace Component
 *
 * Real-time collaborative workspace with:
 * - Real-time collaborative document editing
 * - Project management tools for student groups
 * - Virtual classroom integration
 * - Screen sharing and whiteboard capabilities
 * - Recording and playback functionality
 * - Integration with learning management systems
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  Button,
  Input,
  Select,
  Tabs,
  List,
  Avatar,
  Badge,
  Tag,
  Space,
  Modal,
  Form,
  Upload,
  Tooltip,
  Drawer,
  Switch,
  Slider,
  ColorPicker,
  Popover,
  Timeline,
  Progress,
  Spin,
  Alert,
  message,
  notification,
  Dropdown,
  Menu,
  DatePicker,
  Radio,
  Checkbox,
  Divider,
  Typography,
  Affix,
  FloatButton,
} from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  ShareAltOutlined,
  UserOutlined,
  TeamOutlined,
  VideoRecorder,
  DesktopOutlined,
  BgColorsOutlined,
  PlusOutlined,
  DeleteOutlined,
  CopyOutlined,
  UndoOutlined,
  RedoOutlined,
  ZoomInOutlined,
  ZoomOutOutlined,
  DragOutlined,
  FileTextOutlined,
  PlayCircleOutlined,
  PauseCircleOutlined,
  StopOutlined,
  VideoCameraOutlined,
  AudioOutlined,
  MutedOutlined,
  SoundOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  CommentOutlined,
  HistoryOutlined,
  SettingOutlined,
  LockOutlined,
  UnlockOutlined,
  EyeOutlined,
  EditFilled,
  HighlightOutlined,
  FontColorsOutlined,
  FontSizeOutlined,
  BoldOutlined,
  ItalicOutlined,
  UnderlineOutlined,
  AlignLeftOutlined,
  AlignCenterOutlined,
  AlignRightOutlined,
  OrderedListOutlined,
  UnorderedListOutlined,
  LinkOutlined,
  PictureOutlined,
  TableOutlined,
  CloseOutlined,
  MoreOutlined,
  CloudUploadOutlined,
  DownloadOutlined,
  PrinterOutlined,
  ExportOutlined,
  ImportOutlined,
  SearchOutlined,
  FilterOutlined,
  CalendarOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
  StarOutlined,
  HeartOutlined,
  ThumbsUpOutlined,
} from '@ant-design/icons';
import { motion, AnimatePresence } from 'framer-motion';
import moment from 'moment';
import { useSocket } from '../../../utils/communication/socketManager';

const { TextArea } = Input;
const { TabPane } = Tabs;
const { Option } = Select;
const { Title, Text, Paragraph } = Typography;

interface CollaborativeDocument {
  id: string;
  title: string;
  content: string;
  type: 'document' | 'presentation' | 'spreadsheet' | 'whiteboard' | 'notes';
  createdBy: string;
  createdAt: Date;
  lastModified: Date;
  collaborators: string[];
  permissions: {
    [userId: string]: 'view' | 'comment' | 'edit' | 'admin';
  };
  version: number;
  locked: boolean;
  lockedBy?: string;
  tags: string[];
  folder?: string;
}

interface Cursor {
  userId: string;
  position: {
    line: number;
    column: number;
  };
  selection?: {
    start: { line: number; column: number };
    end: { line: number; column: number };
  };
  color: string;
}

interface Comment {
  id: string;
  documentId: string;
  userId: string;
  content: string;
  position: {
    line: number;
    column: number;
  };
  timestamp: Date;
  resolved: boolean;
  replies: CommentReply[];
}

interface CommentReply {
  id: string;
  userId: string;
  content: string;
  timestamp: Date;
}

interface DocumentChange {
  id: string;
  documentId: string;
  userId: string;
  type: 'insert' | 'delete' | 'format';
  position: {
    line: number;
    column: number;
  };
  content?: string;
  length?: number;
  format?: any;
  timestamp: Date;
}

interface ProjectTask {
  id: string;
  projectId: string;
  title: string;
  description: string;
  assignedTo: string[];
  status: 'todo' | 'in_progress' | 'review' | 'done';
  priority: 'low' | 'medium' | 'high' | 'urgent';
  dueDate?: Date;
  createdAt: Date;
  dependencies: string[];
  estimatedHours?: number;
  actualHours?: number;
  attachments: string[];
  comments: string[];
}

interface Project {
  id: string;
  title: string;
  description: string;
  type: 'student_group' | 'class_project' | 'research' | 'assignment';
  members: string[];
  documents: string[];
  tasks: ProjectTask[];
  deadline?: Date;
  createdAt: Date;
  status: 'planning' | 'active' | 'review' | 'completed' | 'archived';
  progress: number;
  visibility: 'private' | 'class' | 'public';
}

interface WhiteboardElement {
  id: string;
  type: 'text' | 'shape' | 'line' | 'image' | 'sticky_note';
  position: { x: number; y: number };
  size: { width: number; height: number };
  content?: string;
  style: {
    fill?: string;
    stroke?: string;
    strokeWidth?: number;
    fontSize?: number;
    fontFamily?: string;
    color?: string;
  };
  rotation?: number;
  locked?: boolean;
}

interface RecordingSession {
  id: string;
  title: string;
  type: 'screen' | 'camera' | 'both';
  startTime: Date;
  endTime?: Date;
  duration?: number;
  fileUrl?: string;
  participants: string[];
  status: 'recording' | 'processing' | 'ready' | 'failed';
  size?: number;
  thumbnailUrl?: string;
}

const CollaborationWorkspace: React.FC = () => {
  // State management
  const [activeProject, setActiveProject] = useState<Project | null>(null);
  const [projects, setProjects] = useState<Project[]>([]);
  const [activeDocument, setActiveDocument] = useState<CollaborativeDocument | null>(null);
  const [documents, setDocuments] = useState<CollaborativeDocument[]>([]);
  const [documentContent, setDocumentContent] = useState('');
  const [cursors, setCursors] = useState<Map<string, Cursor>>(new Map());
  const [comments, setComments] = useState<Comment[]>([]);
  const [changes, setChanges] = useState<DocumentChange[]>([]);
  const [whiteboardElements, setWhiteboardElements] = useState<WhiteboardElement[]>([]);
  const [recordings, setRecordings] = useState<RecordingSession[]>([]);
  const [loading, setLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isScreenSharing, setIsScreenSharing] = useState(false);
  const [activeTab, setActiveTab] = useState('documents');
  const [viewMode, setViewMode] = useState<'edit' | 'preview' | 'comment'>('edit');
  const [zoom, setZoom] = useState(100);
  const [showComments, setShowComments] = useState(true);
  const [showCursors, setShowCursors] = useState(true);
  const [showProjectDrawer, setShowProjectDrawer] = useState(false);
  const [showDocumentModal, setShowDocumentModal] = useState(false);
  const [showRecordingModal, setShowRecordingModal] = useState(false);
  const [selectedTool, setSelectedTool] = useState('select');
  const [selectedColor, setSelectedColor] = useState('#000000');
  const [selectedFontSize, setSelectedFontSize] = useState(14);

  // Refs
  const editorRef = useRef<any>(null);
  const whiteboardRef = useRef<HTMLCanvasElement>(null);
  const recordingRef = useRef<MediaRecorder | null>(null);

  // Forms
  const [projectForm] = Form.useForm();
  const [documentForm] = Form.useForm();

  // Socket connection
  const { socket, isConnected, on, off } = useSocket();

  // Load initial data
  useEffect(() => {
    loadProjects();
    loadDocuments();
    loadRecordings();
    setupSocketListeners();

    return () => {
      cleanupSocketListeners();
    };
  }, []);

  const setupSocketListeners = () => {
    on('document:change', handleDocumentChange);
    on('document:cursor', handleCursorUpdate);
    on('document:lock', handleDocumentLock);
    on('document:unlock', handleDocumentUnlock);
  };

  const cleanupSocketListeners = () => {
    off('document:change');
    off('document:cursor');
    off('document:lock');
    off('document:unlock');
  };

  const loadProjects = async () => {
    try {
      setLoading(true);
      // Mock data - in real implementation, this would be an API call
      const mockProjects: Project[] = [
        {
          id: 'proj_001',
          title: 'Final Research Project',
          description: 'Collaborative research project on sustainable energy solutions',
          type: 'student_group',
          members: ['user_001', 'user_002', 'user_003'],
          documents: ['doc_001', 'doc_002'],
          tasks: [
            {
              id: 'task_001',
              projectId: 'proj_001',
              title: 'Literature Review',
              description: 'Complete comprehensive literature review on solar energy',
              assignedTo: ['user_001'],
              status: 'in_progress',
              priority: 'high',
              dueDate: new Date('2024-10-15'),
              createdAt: new Date('2024-09-20'),
              dependencies: [],
              estimatedHours: 20,
              actualHours: 12,
              attachments: [],
              comments: [],
            },
            {
              id: 'task_002',
              projectId: 'proj_001',
              title: 'Data Collection',
              description: 'Gather experimental data from renewable energy sources',
              assignedTo: ['user_002', 'user_003'],
              status: 'todo',
              priority: 'medium',
              dueDate: new Date('2024-10-20'),
              createdAt: new Date('2024-09-22'),
              dependencies: ['task_001'],
              estimatedHours: 15,
              attachments: [],
              comments: [],
            },
          ],
          deadline: new Date('2024-11-30'),
          createdAt: new Date('2024-09-15'),
          status: 'active',
          progress: 35,
          visibility: 'class',
        },
        {
          id: 'proj_002',
          title: 'Class Presentation',
          description: 'Group presentation on historical analysis',
          type: 'class_project',
          members: ['user_004', 'user_005'],
          documents: ['doc_003'],
          tasks: [],
          deadline: new Date('2024-10-05'),
          createdAt: new Date('2024-09-25'),
          status: 'planning',
          progress: 10,
          visibility: 'private',
        },
      ];

      setProjects(mockProjects);
      if (mockProjects.length > 0) {
        setActiveProject(mockProjects[0]);
      }
    } catch (error) {
      console.error('Failed to load projects:', error);
      message.error('Failed to load projects');
    } finally {
      setLoading(false);
    }
  };

  const loadDocuments = async () => {
    try {
      const mockDocuments: CollaborativeDocument[] = [
        {
          id: 'doc_001',
          title: 'Research Proposal',
          content: '# Sustainable Energy Research\n\nThis document outlines our research approach...',
          type: 'document',
          createdBy: 'user_001',
          createdAt: new Date('2024-09-20'),
          lastModified: new Date('2024-09-26'),
          collaborators: ['user_001', 'user_002', 'user_003'],
          permissions: {
            'user_001': 'admin',
            'user_002': 'edit',
            'user_003': 'edit',
          },
          version: 5,
          locked: false,
          tags: ['research', 'proposal', 'energy'],
          folder: 'Research Project',
        },
        {
          id: 'doc_002',
          title: 'Literature Review',
          content: '# Literature Review\n\n## Introduction\n\nThe field of renewable energy...',
          type: 'document',
          createdBy: 'user_001',
          createdAt: new Date('2024-09-22'),
          lastModified: new Date('2024-09-25'),
          collaborators: ['user_001'],
          permissions: {
            'user_001': 'admin',
          },
          version: 3,
          locked: true,
          lockedBy: 'user_001',
          tags: ['literature', 'review'],
          folder: 'Research Project',
        },
        {
          id: 'doc_003',
          title: 'Presentation Slides',
          content: '',
          type: 'presentation',
          createdBy: 'user_004',
          createdAt: new Date('2024-09-25'),
          lastModified: new Date('2024-09-26'),
          collaborators: ['user_004', 'user_005'],
          permissions: {
            'user_004': 'admin',
            'user_005': 'edit',
          },
          version: 1,
          locked: false,
          tags: ['presentation', 'history'],
          folder: 'Class Project',
        },
      ];

      setDocuments(mockDocuments);
      if (mockDocuments.length > 0) {
        setActiveDocument(mockDocuments[0]);
        setDocumentContent(mockDocuments[0].content);
      }
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const loadRecordings = async () => {
    try {
      const mockRecordings: RecordingSession[] = [
        {
          id: 'rec_001',
          title: 'Project Planning Session',
          type: 'screen',
          startTime: new Date('2024-09-25T14:00:00'),
          endTime: new Date('2024-09-25T15:30:00'),
          duration: 90,
          fileUrl: 'https://recordings.example.com/session1.mp4',
          participants: ['user_001', 'user_002', 'user_003'],
          status: 'ready',
          size: 156789432,
          thumbnailUrl: 'https://recordings.example.com/session1_thumb.jpg',
        },
      ];

      setRecordings(mockRecordings);
    } catch (error) {
      console.error('Failed to load recordings:', error);
    }
  };

  // Socket event handlers
  const handleDocumentChange = useCallback((data: { documentId: string; changes: any; userId: string }) => {
    if (activeDocument && data.documentId === activeDocument.id) {
      // Apply changes to document
      // In a real implementation, this would use operational transformation
      setDocumentContent(prev => {
        // Simple mock implementation
        return prev + data.changes.content || prev;
      });

      // Add to change history
      const change: DocumentChange = {
        id: `change_${Date.now()}`,
        documentId: data.documentId,
        userId: data.userId,
        type: data.changes.type,
        position: data.changes.position,
        content: data.changes.content,
        timestamp: new Date(),
      };

      setChanges(prev => [change, ...prev]);
    }
  }, [activeDocument]);

  const handleCursorUpdate = useCallback((data: { documentId: string; userId: string; position: any }) => {
    if (activeDocument && data.documentId === activeDocument.id) {
      setCursors(prev => {
        const newCursors = new Map(prev);
        newCursors.set(data.userId, {
          userId: data.userId,
          position: data.position,
          color: `hsl(${data.userId.charCodeAt(0) * 137.5 % 360}, 70%, 50%)`,
        });
        return newCursors;
      });
    }
  }, [activeDocument]);

  const handleDocumentLock = useCallback((data: { documentId: string; userId: string; section: string }) => {
    if (activeDocument && data.documentId === activeDocument.id) {
      message.info(`Document section locked by ${data.userId}`);
    }
  }, [activeDocument]);

  const handleDocumentUnlock = useCallback((data: { documentId: string; userId: string; section: string }) => {
    if (activeDocument && data.documentId === activeDocument.id) {
      message.info(`Document section unlocked by ${data.userId}`);
    }
  }, [activeDocument]);

  const saveDocument = useCallback(async () => {
    if (!activeDocument) return;

    try {
      // In real implementation, send changes to server
      setDocuments(prev =>
        prev.map(doc =>
          doc.id === activeDocument.id
            ? {
                ...doc,
                content: documentContent,
                lastModified: new Date(),
                version: doc.version + 1,
              }
            : doc
        )
      );

      message.success('Document saved successfully');
    } catch (error) {
      console.error('Failed to save document:', error);
      message.error('Failed to save document');
    }
  }, [activeDocument, documentContent]);

  const createProject = useCallback(async (values: any) => {
    try {
      const newProject: Project = {
        id: `proj_${Date.now()}`,
        title: values.title,
        description: values.description,
        type: values.type,
        members: values.members || [],
        documents: [],
        tasks: [],
        deadline: values.deadline?.toDate(),
        createdAt: new Date(),
        status: 'planning',
        progress: 0,
        visibility: values.visibility,
      };

      setProjects(prev => [newProject, ...prev]);
      setShowProjectDrawer(false);
      projectForm.resetFields();
      message.success('Project created successfully');
    } catch (error) {
      console.error('Failed to create project:', error);
      message.error('Failed to create project');
    }
  }, [projectForm]);

  const createDocument = useCallback(async (values: any) => {
    try {
      const newDocument: CollaborativeDocument = {
        id: `doc_${Date.now()}`,
        title: values.title,
        content: values.template === 'blank' ? '' : getDocumentTemplate(values.template),
        type: values.type,
        createdBy: 'current_user',
        createdAt: new Date(),
        lastModified: new Date(),
        collaborators: ['current_user'],
        permissions: {
          'current_user': 'admin',
        },
        version: 1,
        locked: false,
        tags: values.tags || [],
        folder: values.folder,
      };

      setDocuments(prev => [newDocument, ...prev]);
      setActiveDocument(newDocument);
      setDocumentContent(newDocument.content);
      setShowDocumentModal(false);
      documentForm.resetFields();
      message.success('Document created successfully');
    } catch (error) {
      console.error('Failed to create document:', error);
      message.error('Failed to create document');
    }
  }, [documentForm]);

  const getDocumentTemplate = (template: string): string => {
    switch (template) {
      case 'research_paper':
        return `# Research Paper Title

## Abstract
Brief summary of the research...

## Introduction
Background and motivation...

## Methodology
Research methods and approach...

## Results
Findings and data analysis...

## Discussion
Interpretation of results...

## Conclusion
Summary and future work...

## References
1. [Reference 1]
2. [Reference 2]`;

      case 'meeting_notes':
        return `# Meeting Notes - ${moment().format('MMMM DD, YYYY')}

**Date**: ${moment().format('MMMM DD, YYYY')}
**Attendees**:

## Agenda
1.
2.
3.

## Discussion Points

## Action Items
- [ ] Task 1 (Assigned to: )
- [ ] Task 2 (Assigned to: )

## Next Meeting
**Date**:
**Time**: `;

      case 'project_proposal':
        return `# Project Proposal

## Project Overview
Brief description of the project...

## Objectives
- Objective 1
- Objective 2
- Objective 3

## Scope
What will be included and excluded...

## Timeline
| Phase | Duration | Deliverables |
|-------|----------|--------------|
| Phase 1 | 2 weeks | |
| Phase 2 | 3 weeks | |

## Resources Required
- Personnel
- Equipment
- Budget

## Success Metrics
How will success be measured...`;

      default:
        return '';
    }
  };

  const startRecording = useCallback(async (type: 'screen' | 'camera' | 'both') => {
    try {
      let stream: MediaStream;

      if (type === 'screen') {
        stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
      } else if (type === 'camera') {
        stream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });
      } else {
        // Both screen and camera
        const screenStream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });
        const cameraStream = await navigator.mediaDevices.getUserMedia({
          video: true,
          audio: true,
        });

        // Combine streams (simplified - real implementation would be more complex)
        stream = screenStream;
      }

      const recorder = new MediaRecorder(stream);
      recordingRef.current = recorder;

      const newRecording: RecordingSession = {
        id: `rec_${Date.now()}`,
        title: `Recording - ${moment().format('YYYY-MM-DD HH:mm')}`,
        type,
        startTime: new Date(),
        participants: ['current_user'],
        status: 'recording',
      };

      setRecordings(prev => [newRecording, ...prev]);
      setIsRecording(true);

      recorder.start();
      message.success('Recording started');

      recorder.ondataavailable = (event) => {
        // Handle recorded data
        console.log('Recording data available:', event.data);
      };

      recorder.onstop = () => {
        setIsRecording(false);
        stream.getTracks().forEach(track => track.stop());

        // Update recording status
        setRecordings(prev =>
          prev.map(rec =>
            rec.id === newRecording.id
              ? {
                  ...rec,
                  endTime: new Date(),
                  duration: Math.floor((new Date().getTime() - rec.startTime.getTime()) / 1000 / 60),
                  status: 'processing',
                }
              : rec
          )
        );

        message.success('Recording stopped');
      };
    } catch (error) {
      console.error('Failed to start recording:', error);
      message.error('Failed to start recording');
    }
  }, []);

  const stopRecording = useCallback(() => {
    if (recordingRef.current && isRecording) {
      recordingRef.current.stop();
    }
  }, [isRecording]);

  const shareScreen = useCallback(async () => {
    try {
      if (isScreenSharing) {
        // Stop screen sharing
        setIsScreenSharing(false);
        message.info('Screen sharing stopped');
      } else {
        // Start screen sharing
        const stream = await navigator.mediaDevices.getDisplayMedia({
          video: true,
          audio: true,
        });

        setIsScreenSharing(true);
        message.success('Screen sharing started');

        stream.getVideoTracks()[0].onended = () => {
          setIsScreenSharing(false);
          message.info('Screen sharing stopped');
        };
      }
    } catch (error) {
      console.error('Screen sharing failed:', error);
      message.error('Screen sharing failed');
    }
  }, [isScreenSharing]);

  const addComment = useCallback((content: string, position: { line: number; column: number }) => {
    if (!activeDocument) return;

    const newComment: Comment = {
      id: `comment_${Date.now()}`,
      documentId: activeDocument.id,
      userId: 'current_user',
      content,
      position,
      timestamp: new Date(),
      resolved: false,
      replies: [],
    };

    setComments(prev => [...prev, newComment]);
    message.success('Comment added');
  }, [activeDocument]);

  const formatText = useCallback((format: string, value?: any) => {
    if (!editorRef.current) return;

    // Apply text formatting
    switch (format) {
      case 'bold':
        document.execCommand('bold');
        break;
      case 'italic':
        document.execCommand('italic');
        break;
      case 'underline':
        document.execCommand('underline');
        break;
      case 'fontSize':
        document.execCommand('fontSize', false, value);
        break;
      case 'foreColor':
        document.execCommand('foreColor', false, value);
        break;
      case 'insertUnorderedList':
        document.execCommand('insertUnorderedList');
        break;
      case 'insertOrderedList':
        document.execCommand('insertOrderedList');
        break;
      case 'justifyLeft':
        document.execCommand('justifyLeft');
        break;
      case 'justifyCenter':
        document.execCommand('justifyCenter');
        break;
      case 'justifyRight':
        document.execCommand('justifyRight');
        break;
      default:
        console.log('Unknown format:', format);
    }
  }, []);

  const getDocumentIcon = (type: string) => {
    switch (type) {
      case 'document': return <FileTextOutlined />;
      case 'presentation': return <DesktopOutlined />;
      case 'spreadsheet': return <TableOutlined />;
      case 'whiteboard': return <BgColorsOutlined />;
      case 'notes': return <EditOutlined />;
      default: return <FileTextOutlined />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active': return 'green';
      case 'planning': return 'blue';
      case 'review': return 'orange';
      case 'completed': return 'purple';
      case 'archived': return 'gray';
      default: return 'gray';
    }
  };

  const getTaskStatusColor = (status: string) => {
    switch (status) {
      case 'todo': return 'gray';
      case 'in_progress': return 'blue';
      case 'review': return 'orange';
      case 'done': return 'green';
      default: return 'gray';
    }
  };

  const getPriorityColor = (priority: string) => {
    switch (priority) {
      case 'urgent': return 'red';
      case 'high': return 'orange';
      case 'medium': return 'blue';
      case 'low': return 'green';
      default: return 'gray';
    }
  };

  return (
    <div className="collaboration-workspace h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <TeamOutlined className="text-purple-600" />
              Collaboration Workspace
            </h1>
            <p className="text-gray-600">
              Real-time collaborative editing and project management
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              type={isRecording ? 'primary' : 'default'}
              danger={isRecording}
              icon={isRecording ? <StopOutlined /> : <PlayCircleOutlined />}
              onClick={isRecording ? stopRecording : () => setShowRecordingModal(true)}
            >
              {isRecording ? 'Stop Recording' : 'Start Recording'}
            </Button>
            <Button
              type={isScreenSharing ? 'primary' : 'default'}
              icon={<DesktopOutlined />}
              onClick={shareScreen}
            >
              {isScreenSharing ? 'Stop Sharing' : 'Share Screen'}
            </Button>
            <Button
              icon={<PlusOutlined />}
              onClick={() => setShowDocumentModal(true)}
            >
              New Document
            </Button>
            <Button
              icon={<TeamOutlined />}
              onClick={() => setShowProjectDrawer(true)}
            >
              New Project
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 bg-gray-50 border-r flex flex-col">
          <Tabs activeKey={activeTab} onChange={setActiveTab} className="px-4 pt-4">
            <TabPane tab="Documents" key="documents">
              <div className="space-y-2">
                <Input
                  placeholder="Search documents..."
                  prefix={<SearchOutlined />}
                />

                <List
                  dataSource={documents}
                  renderItem={(doc) => (
                    <List.Item
                      className={`cursor-pointer transition-colors hover:bg-blue-50 ${
                        activeDocument?.id === doc.id ? 'bg-blue-100 border-blue-300' : ''
                      }`}
                      onClick={() => {
                        setActiveDocument(doc);
                        setDocumentContent(doc.content);
                      }}
                    >
                      <List.Item.Meta
                        avatar={
                          <Badge dot={doc.locked}>
                            <Avatar icon={getDocumentIcon(doc.type)} />
                          </Badge>
                        }
                        title={
                          <div className="flex justify-between items-center">
                            <span className="font-medium">{doc.title}</span>
                            <div className="flex items-center gap-1">
                              {doc.locked && <LockOutlined className="text-red-500" />}
                              <Tag size="small">{doc.type}</Tag>
                            </div>
                          </div>
                        }
                        description={
                          <div>
                            <div className="text-xs text-gray-500">
                              Modified {moment(doc.lastModified).fromNow()}
                            </div>
                            <div className="flex items-center gap-2 mt-1">
                              <span className="text-xs text-gray-400">
                                v{doc.version} • {doc.collaborators.length} collaborators
                              </span>
                            </div>
                          </div>
                        }
                      />
                    </List.Item>
                  )}
                />
              </div>
            </TabPane>

            <TabPane tab="Projects" key="projects">
              <List
                dataSource={projects}
                renderItem={(project) => (
                  <List.Item
                    className={`cursor-pointer hover:bg-gray-50 ${
                      activeProject?.id === project.id ? 'bg-blue-50' : ''
                    }`}
                    onClick={() => setActiveProject(project)}
                  >
                    <List.Item.Meta
                      avatar={<Avatar icon={<TeamOutlined />} />}
                      title={
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{project.title}</span>
                          <Tag color={getStatusColor(project.status)}>
                            {project.status}
                          </Tag>
                        </div>
                      }
                      description={
                        <div>
                          <div className="text-xs text-gray-500 mb-1">
                            {project.description}
                          </div>
                          <Progress
                            percent={project.progress}
                            size="small"
                            showInfo={false}
                          />
                          <div className="flex items-center gap-2 mt-1">
                            <span className="text-xs text-gray-400">
                              {project.members.length} members
                            </span>
                            {project.deadline && (
                              <span className="text-xs text-gray-400">
                                Due {moment(project.deadline).fromNow()}
                              </span>
                            )}
                          </div>
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </TabPane>

            <TabPane tab="Recordings" key="recordings">
              <List
                dataSource={recordings}
                renderItem={(recording) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={
                        <Avatar
                          icon={
                            recording.type === 'screen' ? <DesktopOutlined /> :
                            recording.type === 'camera' ? <VideoCameraOutlined /> :
                            <PlayCircleOutlined />
                          }
                        />
                      }
                      title={recording.title}
                      description={
                        <div>
                          <div className="flex items-center gap-2 mb-1">
                            <Tag color={
                              recording.status === 'ready' ? 'green' :
                              recording.status === 'recording' ? 'blue' :
                              recording.status === 'processing' ? 'orange' : 'red'
                            }>
                              {recording.status}
                            </Tag>
                            <span className="text-xs text-gray-400">
                              {recording.duration ? `${recording.duration} min` : 'In progress'}
                            </span>
                          </div>
                          <div className="text-xs text-gray-500">
                            {moment(recording.startTime).format('MMM DD, HH:mm')}
                          </div>
                        </div>
                      }
                    />
                    {recording.status === 'ready' && (
                      <Button
                        size="small"
                        icon={<PlayCircleOutlined />}
                        onClick={() => window.open(recording.fileUrl, '_blank')}
                      >
                        Play
                      </Button>
                    )}
                  </List.Item>
                )}
              />
            </TabPane>
          </Tabs>
        </div>

        {/* Main Editor Area */}
        <div className="flex-1 flex flex-col">
          {activeDocument ? (
            <>
              {/* Editor Toolbar */}
              <div className="bg-white border-b px-4 py-2">
                <div className="flex justify-between items-center">
                  <div className="flex items-center gap-2">
                    <Button.Group>
                      <Button
                        icon={<SaveOutlined />}
                        type={viewMode === 'edit' ? 'primary' : 'default'}
                        onClick={saveDocument}
                      >
                        Save
                      </Button>
                      <Button
                        icon={<ShareAltOutlined />}
                        onClick={() => {
                          navigator.clipboard.writeText(window.location.href);
                          message.success('Link copied to clipboard');
                        }}
                      >
                        Share
                      </Button>
                      <Button icon={<HistoryOutlined />}>
                        History
                      </Button>
                    </Button.Group>

                    <Divider type="vertical" />

                    <Button.Group>
                      <Button
                        type={viewMode === 'edit' ? 'primary' : 'default'}
                        onClick={() => setViewMode('edit')}
                      >
                        Edit
                      </Button>
                      <Button
                        type={viewMode === 'preview' ? 'primary' : 'default'}
                        onClick={() => setViewMode('preview')}
                      >
                        Preview
                      </Button>
                      <Button
                        type={viewMode === 'comment' ? 'primary' : 'default'}
                        onClick={() => setViewMode('comment')}
                      >
                        Comment
                      </Button>
                    </Button.Group>

                    <Divider type="vertical" />

                    {/* Formatting Toolbar */}
                    <Button.Group>
                      <Button
                        icon={<BoldOutlined />}
                        onClick={() => formatText('bold')}
                      />
                      <Button
                        icon={<ItalicOutlined />}
                        onClick={() => formatText('italic')}
                      />
                      <Button
                        icon={<UnderlineOutlined />}
                        onClick={() => formatText('underline')}
                      />
                    </Button.Group>

                    <Button.Group>
                      <Button
                        icon={<AlignLeftOutlined />}
                        onClick={() => formatText('justifyLeft')}
                      />
                      <Button
                        icon={<AlignCenterOutlined />}
                        onClick={() => formatText('justifyCenter')}
                      />
                      <Button
                        icon={<AlignRightOutlined />}
                        onClick={() => formatText('justifyRight')}
                      />
                    </Button.Group>

                    <Button.Group>
                      <Button
                        icon={<UnorderedListOutlined />}
                        onClick={() => formatText('insertUnorderedList')}
                      />
                      <Button
                        icon={<OrderedListOutlined />}
                        onClick={() => formatText('insertOrderedList')}
                      />
                    </Button.Group>
                  </div>

                  <div className="flex items-center gap-2">
                    <Select
                      size="small"
                      value={selectedFontSize}
                      onChange={setSelectedFontSize}
                      style={{ width: 80 }}
                    >
                      <Option value={10}>10px</Option>
                      <Option value={12}>12px</Option>
                      <Option value={14}>14px</Option>
                      <Option value={16}>16px</Option>
                      <Option value={18}>18px</Option>
                      <Option value={20}>20px</Option>
                      <Option value={24}>24px</Option>
                    </Select>

                    <ColorPicker
                      value={selectedColor}
                      onChange={(color) => setSelectedColor(color.toHexString())}
                      trigger="click"
                    >
                      <Button icon={<FontColorsOutlined />} />
                    </ColorPicker>

                    <Divider type="vertical" />

                    <Button.Group>
                      <Button
                        icon={<ZoomOutOutlined />}
                        onClick={() => setZoom(Math.max(50, zoom - 10))}
                      />
                      <Button size="small">{zoom}%</Button>
                      <Button
                        icon={<ZoomInOutlined />}
                        onClick={() => setZoom(Math.min(200, zoom + 10))}
                      />
                    </Button.Group>

                    <Button
                      icon={<CommentOutlined />}
                      type={showComments ? 'primary' : 'default'}
                      onClick={() => setShowComments(!showComments)}
                    >
                      Comments
                    </Button>
                  </div>
                </div>
              </div>

              {/* Document Header */}
              <div className="bg-gray-50 px-6 py-3 border-b">
                <div className="flex justify-between items-center">
                  <div>
                    <Title level={3} className="mb-0">{activeDocument.title}</Title>
                    <Text type="secondary">
                      Last modified {moment(activeDocument.lastModified).fromNow()} by {activeDocument.createdBy}
                    </Text>
                  </div>
                  <div className="flex items-center gap-2">
                    {activeDocument.locked ? (
                      <Tag color="red" icon={<LockOutlined />}>
                        Locked by {activeDocument.lockedBy}
                      </Tag>
                    ) : (
                      <Tag color="green" icon={<UnlockOutlined />}>
                        Available for editing
                      </Tag>
                    )}
                    <Tag>v{activeDocument.version}</Tag>
                    <Tag>{activeDocument.collaborators.length} collaborators</Tag>
                  </div>
                </div>
              </div>

              {/* Editor Content */}
              <div className="flex-1 flex overflow-hidden">
                {/* Main Editor */}
                <div
                  className="flex-1 p-6 overflow-y-auto"
                  style={{ fontSize: `${zoom}%` }}
                >
                  {viewMode === 'edit' ? (
                    <div
                      ref={editorRef}
                      contentEditable
                      className="min-h-full w-full outline-none"
                      style={{
                        fontFamily: 'Inter, system-ui, sans-serif',
                        lineHeight: '1.6',
                        fontSize: selectedFontSize,
                        color: selectedColor,
                      }}
                      dangerouslySetInnerHTML={{ __html: documentContent }}
                      onInput={(e) => {
                        const content = e.currentTarget.innerHTML;
                        setDocumentContent(content);

                        // Send changes via socket
                        socket?.sendDocumentChange(activeDocument.id, {
                          type: 'insert',
                          content,
                          position: { line: 0, column: 0 },
                        });
                      }}
                      onKeyDown={(e) => {
                        // Handle special keys
                        if (e.ctrlKey || e.metaKey) {
                          switch (e.key) {
                            case 's':
                              e.preventDefault();
                              saveDocument();
                              break;
                            case 'b':
                              e.preventDefault();
                              formatText('bold');
                              break;
                            case 'i':
                              e.preventDefault();
                              formatText('italic');
                              break;
                            case 'u':
                              e.preventDefault();
                              formatText('underline');
                              break;
                          }
                        }
                      }}
                    />
                  ) : (
                    <div
                      className="prose max-w-none"
                      dangerouslySetInnerHTML={{ __html: documentContent }}
                    />
                  )}

                  {/* Collaborative Cursors */}
                  {showCursors && Array.from(cursors.values()).map((cursor) => (
                    <div
                      key={cursor.userId}
                      className="absolute pointer-events-none"
                      style={{
                        left: cursor.position.column * 8 + 'px',
                        top: cursor.position.line * 24 + 'px',
                        borderLeft: `2px solid ${cursor.color}`,
                        height: '20px',
                      }}
                    >
                      <div
                        className="text-xs text-white px-1 rounded"
                        style={{ backgroundColor: cursor.color }}
                      >
                        {cursor.userId}
                      </div>
                    </div>
                  ))}
                </div>

                {/* Comments Sidebar */}
                {showComments && (
                  <div className="w-80 bg-gray-50 border-l p-4 overflow-y-auto">
                    <div className="flex justify-between items-center mb-4">
                      <h3 className="text-lg font-semibold">Comments</h3>
                      <Button
                        size="small"
                        type="primary"
                        icon={<PlusOutlined />}
                        onClick={() => {
                          const content = prompt('Add a comment:');
                          if (content) {
                            addComment(content, { line: 0, column: 0 });
                          }
                        }}
                      >
                        Add
                      </Button>
                    </div>

                    <div className="space-y-3">
                      {comments
                        .filter(comment => comment.documentId === activeDocument.id)
                        .map((comment) => (
                          <Card key={comment.id} size="small">
                            <div className="flex justify-between items-start mb-2">
                              <div className="flex items-center gap-2">
                                <Avatar size="small" icon={<UserOutlined />} />
                                <span className="text-sm font-medium">{comment.userId}</span>
                              </div>
                              <div className="flex items-center gap-1">
                                <span className="text-xs text-gray-500">
                                  {moment(comment.timestamp).fromNow()}
                                </span>
                                {!comment.resolved && (
                                  <Button
                                    size="small"
                                    type="link"
                                    onClick={() => {
                                      setComments(prev =>
                                        prev.map(c =>
                                          c.id === comment.id ? { ...c, resolved: true } : c
                                        )
                                      );
                                    }}
                                  >
                                    Resolve
                                  </Button>
                                )}
                              </div>
                            </div>
                            <p className="text-sm text-gray-700 mb-2">{comment.content}</p>
                            {comment.resolved && (
                              <Tag size="small" color="green">Resolved</Tag>
                            )}
                          </Card>
                        ))}

                      {comments.filter(c => c.documentId === activeDocument.id).length === 0 && (
                        <div className="text-center text-gray-500 py-8">
                          <CommentOutlined className="text-2xl mb-2" />
                          <p>No comments yet</p>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <FileTextOutlined className="text-6xl text-gray-300 mb-4" />
                <h3 className="text-lg font-semibold text-gray-500">
                  Select a Document
                </h3>
                <p className="text-gray-400">
                  Choose a document from the sidebar to start editing
                </p>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setShowDocumentModal(true)}
                  className="mt-4"
                >
                  Create New Document
                </Button>
              </div>
            </div>
          )}
        </div>

        {/* Project Tasks Panel */}
        {activeProject && (
          <div className="w-80 bg-gray-50 border-l flex flex-col">
            <div className="p-4 border-b">
              <div className="flex justify-between items-center mb-2">
                <h3 className="text-lg font-semibold">{activeProject.title}</h3>
                <Tag color={getStatusColor(activeProject.status)}>
                  {activeProject.status}
                </Tag>
              </div>
              <Progress percent={activeProject.progress} size="small" />
            </div>

            <div className="flex-1 overflow-y-auto p-4">
              <div className="space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="font-semibold">Tasks</h4>
                  <Button size="small" icon={<PlusOutlined />}>
                    Add Task
                  </Button>
                </div>

                {activeProject.tasks.map((task) => (
                  <Card key={task.id} size="small">
                    <div className="flex justify-between items-start mb-2">
                      <span className="font-medium">{task.title}</span>
                      <div className="flex items-center gap-1">
                        <Tag color={getTaskStatusColor(task.status)} size="small">
                          {task.status.replace('_', ' ')}
                        </Tag>
                        <Tag color={getPriorityColor(task.priority)} size="small">
                          {task.priority}
                        </Tag>
                      </div>
                    </div>
                    <p className="text-sm text-gray-600 mb-2">{task.description}</p>
                    {task.dueDate && (
                      <div className="text-xs text-gray-500 mb-2">
                        Due: {moment(task.dueDate).format('MMM DD, YYYY')}
                      </div>
                    )}
                    <div className="flex justify-between items-center">
                      <span className="text-xs text-gray-500">
                        {task.assignedTo.length} assigned
                      </span>
                      {task.estimatedHours && (
                        <span className="text-xs text-gray-500">
                          {task.actualHours || 0}/{task.estimatedHours}h
                        </span>
                      )}
                    </div>
                  </Card>
                ))}

                {activeProject.tasks.length === 0 && (
                  <div className="text-center text-gray-500 py-8">
                    <CheckCircleOutlined className="text-2xl mb-2" />
                    <p>No tasks yet</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Create Document Modal */}
      <Modal
        title="Create New Document"
        open={showDocumentModal}
        onCancel={() => {
          setShowDocumentModal(false);
          documentForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={documentForm}
          layout="vertical"
          onFinish={createDocument}
        >
          <Form.Item
            name="title"
            label="Document Title"
            rules={[{ required: true, message: 'Please enter document title' }]}
          >
            <Input placeholder="e.g., Research Proposal" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="type"
                label="Document Type"
                rules={[{ required: true, message: 'Please select document type' }]}
              >
                <Select>
                  <Option value="document">Document</Option>
                  <Option value="presentation">Presentation</Option>
                  <Option value="spreadsheet">Spreadsheet</Option>
                  <Option value="whiteboard">Whiteboard</Option>
                  <Option value="notes">Notes</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="template"
                label="Template"
              >
                <Select placeholder="Choose a template">
                  <Option value="blank">Blank Document</Option>
                  <Option value="research_paper">Research Paper</Option>
                  <Option value="meeting_notes">Meeting Notes</Option>
                  <Option value="project_proposal">Project Proposal</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="folder"
            label="Folder"
          >
            <Input placeholder="Optional folder organization" />
          </Form.Item>

          <Form.Item
            name="tags"
            label="Tags"
          >
            <Select
              mode="tags"
              placeholder="Add tags for organization"
            >
              <Option value="research">research</Option>
              <Option value="presentation">presentation</Option>
              <Option value="assignment">assignment</Option>
              <Option value="notes">notes</Option>
            </Select>
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowDocumentModal(false);
              documentForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Create Document
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Create Project Drawer */}
      <Drawer
        title="Create New Project"
        placement="right"
        width={500}
        open={showProjectDrawer}
        onClose={() => {
          setShowProjectDrawer(false);
          projectForm.resetFields();
        }}
      >
        <Form
          form={projectForm}
          layout="vertical"
          onFinish={createProject}
        >
          <Form.Item
            name="title"
            label="Project Title"
            rules={[{ required: true, message: 'Please enter project title' }]}
          >
            <Input placeholder="e.g., Final Research Project" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
            rules={[{ required: true, message: 'Please enter project description' }]}
          >
            <TextArea rows={3} placeholder="Brief description of the project" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="type"
                label="Project Type"
                rules={[{ required: true, message: 'Please select project type' }]}
              >
                <Select>
                  <Option value="student_group">Student Group</Option>
                  <Option value="class_project">Class Project</Option>
                  <Option value="research">Research</Option>
                  <Option value="assignment">Assignment</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="visibility"
                label="Visibility"
                rules={[{ required: true, message: 'Please select visibility' }]}
              >
                <Select>
                  <Option value="private">Private</Option>
                  <Option value="class">Class</Option>
                  <Option value="public">Public</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="deadline"
            label="Deadline (Optional)"
          >
            <DatePicker style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item
            name="members"
            label="Team Members"
          >
            <Select
              mode="multiple"
              placeholder="Add team members"
              // In real implementation, this would load from user database
            >
              <Option value="user_001">Sarah Johnson</Option>
              <Option value="user_002">Michael Chen</Option>
              <Option value="user_003">Emily Rodriguez</Option>
            </Select>
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowProjectDrawer(false);
              projectForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Create Project
            </Button>
          </div>
        </Form>
      </Drawer>

      {/* Recording Modal */}
      <Modal
        title="Start Recording"
        open={showRecordingModal}
        onCancel={() => setShowRecordingModal(false)}
        footer={null}
        width={400}
      >
        <div className="space-y-4">
          <p>Choose what you'd like to record:</p>

          <div className="space-y-2">
            <Button
              block
              size="large"
              icon={<DesktopOutlined />}
              onClick={() => {
                startRecording('screen');
                setShowRecordingModal(false);
              }}
            >
              Screen Recording
            </Button>

            <Button
              block
              size="large"
              icon={<VideoCameraOutlined />}
              onClick={() => {
                startRecording('camera');
                setShowRecordingModal(false);
              }}
            >
              Camera Recording
            </Button>

            <Button
              block
              size="large"
              icon={<PlayCircleOutlined />}
              onClick={() => {
                startRecording('both');
                setShowRecordingModal(false);
              }}
            >
              Screen + Camera
            </Button>
          </div>
        </div>
      </Modal>

      {/* Floating Action Button for Quick Actions */}
      <FloatButton.Group
        trigger="click"
        type="primary"
        style={{ right: 24 }}
        icon={<PlusOutlined />}
      >
        <FloatButton
          icon={<FileTextOutlined />}
          tooltip="New Document"
          onClick={() => setShowDocumentModal(true)}
        />
        <FloatButton
          icon={<TeamOutlined />}
          tooltip="New Project"
          onClick={() => setShowProjectDrawer(true)}
        />
        <FloatButton
          icon={<PlayCircleOutlined />}
          tooltip="Start Recording"
          onClick={() => setShowRecordingModal(true)}
        />
      </FloatButton.Group>
    </div>
  );
};

export default CollaborationWorkspace;