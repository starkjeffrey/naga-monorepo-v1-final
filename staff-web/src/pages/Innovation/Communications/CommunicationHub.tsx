/**
 * CommunicationHub Component
 *
 * Unified communication system with:
 * - Unified messaging system with threading and organization
 * - Video call scheduling with calendar integration
 * - Announcement broadcasting with read receipts
 * - Parent/guardian communication portal
 * - Multi-language support with auto-translation
 * - Integration with external communication platforms
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Row,
  Col,
  List,
  Avatar,
  Button,
  Input,
  Select,
  Badge,
  Tag,
  Space,
  Modal,
  Form,
  Upload,
  Tabs,
  Timeline,
  Tooltip,
  Drawer,
  Switch,
  Radio,
  Checkbox,
  DatePicker,
  TimePicker,
  Divider,
  Alert,
  Dropdown,
  Menu,
  Progress,
  Spin,
  Empty,
  Popover,
  message,
  notification,
} from 'antd';
import {
  MessageOutlined,
  SendOutlined,
  PhoneOutlined,
  VideoCameraOutlined,
  CalendarOutlined,
  UserOutlined,
  TeamOutlined,
  SettingOutlined,
  PlusOutlined,
  SearchOutlined,
  FilterOutlined,
  TranslationOutlined,
  BellOutlined,
  PaperClipOutlined,
  SmileOutlined,
  MoreOutlined,
  ReadOutlined,
  EyeOutlined,
  CloseOutlined,
  EditOutlined,
  DeleteOutlined,
  ShareAltOutlined,
  FlagOutlined,
  SoundOutlined,
  MutedOutlined,
  GlobalOutlined,
  LockOutlined,
  UnlockOutlined,
  StarOutlined,
  HeartOutlined,
  ThunderboltOutlined,
  ClockCircleOutlined,
  CheckCircleOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import { motion, AnimatePresence } from 'framer-motion';
import moment from 'moment';
import { useSocket } from '../../../utils/communication/socketManager';
import { Message, CommunicationChannel } from '../../../types/innovation';

const { TextArea } = Input;
const { TabPane } = Tabs;
const { Option } = Select;
const { RangePicker } = DatePicker;

interface ChatUser {
  id: string;
  name: string;
  avatar?: string;
  status: 'online' | 'away' | 'busy' | 'offline';
  role: 'student' | 'teacher' | 'admin' | 'parent' | 'staff';
  lastSeen?: Date;
  isTyping?: boolean;
}

interface VideoCall {
  id: string;
  title: string;
  participants: string[];
  scheduledTime: Date;
  duration: number;
  status: 'scheduled' | 'ongoing' | 'completed' | 'cancelled';
  recordingUrl?: string;
  meetingLink: string;
}

interface Announcement {
  id: string;
  title: string;
  content: string;
  author: string;
  createdAt: Date;
  priority: 'low' | 'medium' | 'high' | 'urgent';
  targetAudience: string[];
  readBy: Array<{
    userId: string;
    readAt: Date;
  }>;
  expiresAt?: Date;
  pinned: boolean;
  attachments?: string[];
}

interface Translation {
  originalText: string;
  translatedText: string;
  sourceLanguage: string;
  targetLanguage: string;
  confidence: number;
}

const CommunicationHub: React.FC = () => {
  // State management
  const [activeChannel, setActiveChannel] = useState<CommunicationChannel | null>(null);
  const [channels, setChannels] = useState<CommunicationChannel[]>([]);
  const [messages, setMessages] = useState<Map<string, Message[]>>(new Map());
  const [users, setUsers] = useState<ChatUser[]>([]);
  const [announcements, setAnnouncements] = useState<Announcement[]>([]);
  const [videoCalls, setVideoCalls] = useState<VideoCall[]>([]);
  const [loading, setLoading] = useState(false);
  const [messageInput, setMessageInput] = useState('');
  const [isTyping, setIsTyping] = useState(false);
  const [showChannelModal, setShowChannelModal] = useState(false);
  const [showAnnouncementModal, setShowAnnouncementModal] = useState(false);
  const [showCallModal, setShowCallModal] = useState(false);
  const [showSettingsDrawer, setShowSettingsDrawer] = useState(false);
  const [selectedLanguage, setSelectedLanguage] = useState('en');
  const [autoTranslate, setAutoTranslate] = useState(false);
  const [notificationsEnabled, setNotificationsEnabled] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  const [searchQuery, setSearchQuery] = useState('');
  const [filters, setFilters] = useState({
    unreadOnly: false,
    priority: 'all',
    dateRange: null as any,
  });

  // Refs
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const typingTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Forms
  const [channelForm] = Form.useForm();
  const [announcementForm] = Form.useForm();
  const [callForm] = Form.useForm();

  // Socket connection
  const { socket, isConnected, on, off } = useSocket();

  // Load initial data
  useEffect(() => {
    loadChannels();
    loadUsers();
    loadAnnouncements();
    loadVideoCalls();
    setupSocketListeners();

    return () => {
      cleanupSocketListeners();
    };
  }, []);

  // Auto-scroll to bottom of messages
  useEffect(() => {
    scrollToBottom();
  }, [messages, activeChannel]);

  const setupSocketListeners = () => {
    on('message:new', handleNewMessage);
    on('message:read', handleMessageRead);
    on('message:typing', handleTypingIndicator);
    on('channel:joined', handleChannelJoined);
    on('channel:left', handleChannelLeft);
    on('user:online', handleUserStatusChange);
    on('user:offline', handleUserStatusChange);
    on('call:incoming', handleIncomingCall);
  };

  const cleanupSocketListeners = () => {
    off('message:new');
    off('message:read');
    off('message:typing');
    off('channel:joined');
    off('channel:left');
    off('user:online');
    off('user:offline');
    off('call:incoming');
  };

  const loadChannels = async () => {
    try {
      setLoading(true);
      // Mock data - in real implementation, this would be an API call
      const mockChannels: CommunicationChannel[] = [
        {
          id: 'chan_001',
          name: 'General Discussion',
          type: 'public',
          description: 'General communication for all staff and students',
          memberIds: ['user_001', 'user_002', 'user_003'],
          admins: ['user_001'],
          settings: {
            allowFiles: true,
            allowVideoCalls: true,
            autoTranslate: false,
            retentionDays: 30,
          },
          createdAt: new Date('2024-09-01'),
        },
        {
          id: 'chan_002',
          name: 'Academic Affairs',
          type: 'department',
          description: 'Academic department communications',
          memberIds: ['user_001', 'user_004', 'user_005'],
          admins: ['user_004'],
          settings: {
            allowFiles: true,
            allowVideoCalls: true,
            autoTranslate: true,
            retentionDays: 90,
          },
          createdAt: new Date('2024-09-05'),
        },
        {
          id: 'chan_003',
          name: 'Student Support',
          type: 'private',
          description: 'Private channel for student support team',
          memberIds: ['user_002', 'user_006'],
          admins: ['user_002'],
          settings: {
            allowFiles: true,
            allowVideoCalls: false,
            autoTranslate: false,
            retentionDays: 60,
          },
          createdAt: new Date('2024-09-10'),
        },
      ];

      setChannels(mockChannels);
      if (mockChannels.length > 0) {
        setActiveChannel(mockChannels[0]);
        loadMessages(mockChannels[0].id);
      }
    } catch (error) {
      console.error('Failed to load channels:', error);
      message.error('Failed to load communication channels');
    } finally {
      setLoading(false);
    }
  };

  const loadUsers = async () => {
    try {
      const mockUsers: ChatUser[] = [
        {
          id: 'user_001',
          name: 'Dr. Sarah Wilson',
          avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=sarah',
          status: 'online',
          role: 'teacher',
          lastSeen: new Date(),
        },
        {
          id: 'user_002',
          name: 'Michael Brown',
          avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=michael',
          status: 'away',
          role: 'admin',
          lastSeen: new Date(Date.now() - 10 * 60 * 1000),
        },
        {
          id: 'user_003',
          name: 'Emily Rodriguez',
          avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=emily',
          status: 'online',
          role: 'student',
          lastSeen: new Date(),
        },
        {
          id: 'user_004',
          name: 'Prof. James Chen',
          avatar: 'https://api.dicebear.com/7.x/avataaars/svg?seed=james',
          status: 'busy',
          role: 'teacher',
          lastSeen: new Date(Date.now() - 5 * 60 * 1000),
        },
      ];

      setUsers(mockUsers);
    } catch (error) {
      console.error('Failed to load users:', error);
    }
  };

  const loadMessages = async (channelId: string) => {
    try {
      // Mock messages
      const mockMessages: Message[] = [
        {
          id: 'msg_001',
          senderId: 'user_001',
          recipientIds: ['user_002', 'user_003'],
          subject: 'Welcome to the channel',
          content: 'Welcome everyone to our communication hub!',
          type: 'direct',
          priority: 'normal',
          timestamp: new Date('2024-09-26T08:00:00'),
          readBy: [
            { userId: 'user_002', readAt: new Date('2024-09-26T08:05:00') },
          ],
          tags: ['welcome'],
        },
        {
          id: 'msg_002',
          senderId: 'user_003',
          recipientIds: ['user_001'],
          content: 'Thank you! This looks great.',
          type: 'direct',
          priority: 'normal',
          timestamp: new Date('2024-09-26T08:10:00'),
          readBy: [],
          parentMessageId: 'msg_001',
        },
        {
          id: 'msg_003',
          senderId: 'user_002',
          recipientIds: ['user_001', 'user_003'],
          content: 'I have some questions about the upcoming semester schedule.',
          type: 'direct',
          priority: 'high',
          timestamp: new Date('2024-09-26T09:00:00'),
          readBy: [],
        },
      ];

      setMessages(prev => new Map(prev).set(channelId, mockMessages));
    } catch (error) {
      console.error('Failed to load messages:', error);
    }
  };

  const loadAnnouncements = async () => {
    try {
      const mockAnnouncements: Announcement[] = [
        {
          id: 'ann_001',
          title: 'Important: Fall Semester Registration',
          content: 'Fall semester registration begins on October 1st. Please ensure all students complete their course selections by the deadline.',
          author: 'Registrar Office',
          createdAt: new Date('2024-09-25T10:00:00'),
          priority: 'high',
          targetAudience: ['all_staff', 'all_students'],
          readBy: [
            { userId: 'user_001', readAt: new Date('2024-09-25T10:30:00') },
            { userId: 'user_002', readAt: new Date('2024-09-25T11:00:00') },
          ],
          pinned: true,
          attachments: ['registration_guide.pdf'],
        },
        {
          id: 'ann_002',
          title: 'System Maintenance Notice',
          content: 'The student information system will be down for maintenance on September 30th from 2:00 AM to 6:00 AM.',
          author: 'IT Department',
          createdAt: new Date('2024-09-24T14:00:00'),
          priority: 'medium',
          targetAudience: ['all_users'],
          readBy: [],
          expiresAt: new Date('2024-09-30T06:00:00'),
          pinned: false,
        },
      ];

      setAnnouncements(mockAnnouncements);
    } catch (error) {
      console.error('Failed to load announcements:', error);
    }
  };

  const loadVideoCalls = async () => {
    try {
      const mockCalls: VideoCall[] = [
        {
          id: 'call_001',
          title: 'Weekly Team Meeting',
          participants: ['user_001', 'user_002', 'user_004'],
          scheduledTime: new Date('2024-09-27T14:00:00'),
          duration: 60,
          status: 'scheduled',
          meetingLink: 'https://meet.example.com/weekly-team',
        },
        {
          id: 'call_002',
          title: 'Student Advisory Session',
          participants: ['user_003', 'user_001'],
          scheduledTime: new Date('2024-09-26T15:30:00'),
          duration: 30,
          status: 'completed',
          meetingLink: 'https://meet.example.com/advisory-session',
          recordingUrl: 'https://recordings.example.com/advisory-session.mp4',
        },
      ];

      setVideoCalls(mockCalls);
    } catch (error) {
      console.error('Failed to load video calls:', error);
    }
  };

  // Socket event handlers
  const handleNewMessage = useCallback((message: Message) => {
    if (activeChannel) {
      setMessages(prev => {
        const channelMessages = prev.get(activeChannel.id) || [];
        return new Map(prev).set(activeChannel.id, [...channelMessages, message]);
      });
    }

    // Show notification if enabled
    if (notificationsEnabled && message.senderId !== 'current_user') {
      const sender = users.find(u => u.id === message.senderId);
      notification.open({
        message: sender?.name || 'New Message',
        description: message.content,
        icon: <MessageOutlined style={{ color: '#108ee9' }} />,
        placement: 'topRight',
      });
    }
  }, [activeChannel, notificationsEnabled, users]);

  const handleMessageRead = useCallback((data: { messageId: string; userId: string; readAt: Date }) => {
    if (activeChannel) {
      setMessages(prev => {
        const channelMessages = prev.get(activeChannel.id) || [];
        const updatedMessages = channelMessages.map(msg =>
          msg.id === data.messageId
            ? {
                ...msg,
                readBy: [...msg.readBy, { userId: data.userId, readAt: data.readAt }]
              }
            : msg
        );
        return new Map(prev).set(activeChannel.id, updatedMessages);
      });
    }
  }, [activeChannel]);

  const handleTypingIndicator = useCallback((data: { channelId: string; userId: string; isTyping: boolean }) => {
    if (data.channelId === activeChannel?.id) {
      setUsers(prev =>
        prev.map(user =>
          user.id === data.userId
            ? { ...user, isTyping: data.isTyping }
            : user
        )
      );
    }
  }, [activeChannel]);

  const handleChannelJoined = useCallback((data: { channelId: string; userId: string }) => {
    // Update channel membership
    setChannels(prev =>
      prev.map(channel =>
        channel.id === data.channelId
          ? { ...channel, memberIds: [...channel.memberIds, data.userId] }
          : channel
      )
    );
  }, []);

  const handleChannelLeft = useCallback((data: { channelId: string; userId: string }) => {
    // Update channel membership
    setChannels(prev =>
      prev.map(channel =>
        channel.id === data.channelId
          ? { ...channel, memberIds: channel.memberIds.filter(id => id !== data.userId) }
          : channel
      )
    );
  }, []);

  const handleUserStatusChange = useCallback((data: { userId: string; status?: string }) => {
    setUsers(prev =>
      prev.map(user =>
        user.id === data.userId
          ? { ...user, status: (data.status as any) || 'offline', lastSeen: new Date() }
          : user
      )
    );
  }, []);

  const handleIncomingCall = useCallback((data: { callId: string; from: string; channelId?: string }) => {
    const caller = users.find(u => u.id === data.from);
    Modal.confirm({
      title: 'Incoming Video Call',
      content: `${caller?.name || 'Unknown'} is calling you`,
      okText: 'Accept',
      cancelText: 'Decline',
      onOk: () => {
        socket?.acceptCall(data.callId);
        // Open video call window
        window.open(`/video-call/${data.callId}`, '_blank');
      },
      onCancel: () => {
        socket?.rejectCall(data.callId);
      },
    });
  }, [users, socket]);

  const sendMessage = useCallback(async () => {
    if (!messageInput.trim() || !activeChannel) return;

    const newMessage: Omit<Message, 'id' | 'timestamp'> = {
      senderId: 'current_user', // In real app, get from auth context
      recipientIds: activeChannel.memberIds,
      content: messageInput,
      type: 'direct',
      priority: 'normal',
      readBy: [],
    };

    // Send via socket
    socket?.sendMessage(newMessage);

    // Clear input
    setMessageInput('');
    setIsTyping(false);
  }, [messageInput, activeChannel, socket]);

  const handleTyping = useCallback((value: string) => {
    setMessageInput(value);

    if (!isTyping && value.trim()) {
      setIsTyping(true);
      socket?.setTyping(activeChannel?.id || '', true);
    }

    // Clear existing timeout
    if (typingTimeoutRef.current) {
      clearTimeout(typingTimeoutRef.current);
    }

    // Set new timeout
    typingTimeoutRef.current = setTimeout(() => {
      setIsTyping(false);
      socket?.setTyping(activeChannel?.id || '', false);
    }, 1000);
  }, [isTyping, activeChannel, socket]);

  const createChannel = useCallback(async (values: any) => {
    try {
      const newChannel: CommunicationChannel = {
        id: `chan_${Date.now()}`,
        name: values.name,
        type: values.type,
        description: values.description,
        memberIds: values.members || [],
        admins: ['current_user'],
        settings: {
          allowFiles: values.allowFiles,
          allowVideoCalls: values.allowVideoCalls,
          autoTranslate: values.autoTranslate,
          retentionDays: values.retentionDays,
        },
        createdAt: new Date(),
      };

      setChannels(prev => [newChannel, ...prev]);
      setShowChannelModal(false);
      channelForm.resetFields();
      message.success('Channel created successfully');

      // Join the new channel
      socket?.joinChannel(newChannel.id);
    } catch (error) {
      console.error('Failed to create channel:', error);
      message.error('Failed to create channel');
    }
  }, [channelForm, socket]);

  const createAnnouncement = useCallback(async (values: any) => {
    try {
      const newAnnouncement: Announcement = {
        id: `ann_${Date.now()}`,
        title: values.title,
        content: values.content,
        author: 'Current User',
        createdAt: new Date(),
        priority: values.priority,
        targetAudience: values.targetAudience,
        readBy: [],
        expiresAt: values.expiresAt,
        pinned: values.pinned || false,
        attachments: values.attachments || [],
      };

      setAnnouncements(prev => [newAnnouncement, ...prev]);
      setShowAnnouncementModal(false);
      announcementForm.resetFields();
      message.success('Announcement created successfully');
    } catch (error) {
      console.error('Failed to create announcement:', error);
      message.error('Failed to create announcement');
    }
  }, [announcementForm]);

  const scheduleVideoCall = useCallback(async (values: any) => {
    try {
      const newCall: VideoCall = {
        id: `call_${Date.now()}`,
        title: values.title,
        participants: values.participants,
        scheduledTime: values.scheduledTime.toDate(),
        duration: values.duration,
        status: 'scheduled',
        meetingLink: `https://meet.example.com/${Date.now()}`,
      };

      setVideoCalls(prev => [newCall, ...prev]);
      setShowCallModal(false);
      callForm.resetFields();
      message.success('Video call scheduled successfully');
    } catch (error) {
      console.error('Failed to schedule call:', error);
      message.error('Failed to schedule call');
    }
  }, [callForm]);

  const translateMessage = useCallback(async (messageId: string, targetLanguage: string) => {
    try {
      // Mock translation - in real implementation, use translation API
      const translation: Translation = {
        originalText: 'Hello, how are you?',
        translatedText: 'Hola, ¿cómo estás?',
        sourceLanguage: 'en',
        targetLanguage,
        confidence: 0.95,
      };

      message.success(`Translated to ${targetLanguage}: ${translation.translatedText}`);
    } catch (error) {
      console.error('Translation failed:', error);
      message.error('Translation failed');
    }
  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'online': return 'green';
      case 'away': return 'orange';
      case 'busy': return 'red';
      default: return 'gray';
    }
  };

  const getUserRole = (role: string) => {
    switch (role) {
      case 'teacher': return { color: 'blue', text: 'Teacher' };
      case 'admin': return { color: 'purple', text: 'Admin' };
      case 'student': return { color: 'green', text: 'Student' };
      case 'parent': return { color: 'orange', text: 'Parent' };
      default: return { color: 'gray', text: 'Staff' };
    }
  };

  const currentChannelMessages = activeChannel ? messages.get(activeChannel.id) || [] : [];
  const typingUsers = users.filter(u => u.isTyping);

  return (
    <div className="communication-hub h-screen flex flex-col">
      {/* Header */}
      <div className="bg-white border-b px-6 py-4">
        <div className="flex justify-between items-center">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-3">
              <MessageOutlined className="text-blue-600" />
              Communication Hub
            </h1>
            <p className="text-gray-600">
              {isConnected ? (
                <Badge status="success" text="Connected" />
              ) : (
                <Badge status="error" text="Disconnected" />
              )}
            </p>
          </div>
          <div className="flex gap-2">
            <Button
              icon={<PlusOutlined />}
              onClick={() => setShowChannelModal(true)}
            >
              New Channel
            </Button>
            <Button
              icon={<BellOutlined />}
              onClick={() => setShowAnnouncementModal(true)}
            >
              New Announcement
            </Button>
            <Button
              icon={<VideoCameraOutlined />}
              onClick={() => setShowCallModal(true)}
            >
              Schedule Call
            </Button>
            <Button
              icon={<SettingOutlined />}
              onClick={() => setShowSettingsDrawer(true)}
            >
              Settings
            </Button>
          </div>
        </div>
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Sidebar */}
        <div className="w-80 bg-gray-50 border-r flex flex-col">
          {/* Tabs */}
          <Tabs activeKey={activeTab} onChange={setActiveTab} className="px-4 pt-4">
            <TabPane tab="Channels" key="chat">
              <div className="space-y-2">
                <Input
                  placeholder="Search channels..."
                  prefix={<SearchOutlined />}
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />

                <List
                  dataSource={channels.filter(c =>
                    c.name.toLowerCase().includes(searchQuery.toLowerCase())
                  )}
                  renderItem={(channel) => (
                    <List.Item
                      className={`cursor-pointer transition-colors hover:bg-blue-50 ${
                        activeChannel?.id === channel.id ? 'bg-blue-100 border-blue-300' : ''
                      }`}
                      onClick={() => {
                        setActiveChannel(channel);
                        loadMessages(channel.id);
                        socket?.joinChannel(channel.id);
                      }}
                    >
                      <List.Item.Meta
                        avatar={
                          <Badge dot={channel.type === 'private'}>
                            <Avatar
                              icon={
                                channel.type === 'public' ? <GlobalOutlined /> :
                                channel.type === 'private' ? <LockOutlined /> :
                                <TeamOutlined />
                              }
                            />
                          </Badge>
                        }
                        title={
                          <div className="flex justify-between items-center">
                            <span className="font-medium">{channel.name}</span>
                            <div className="flex items-center gap-1">
                              {channel.settings.autoTranslate && (
                                <TranslationOutlined className="text-blue-500" />
                              )}
                              {channel.settings.allowVideoCalls && (
                                <VideoCameraOutlined className="text-green-500" />
                              )}
                            </div>
                          </div>
                        }
                        description={
                          <div>
                            <div className="text-xs text-gray-500">{channel.description}</div>
                            <div className="flex items-center gap-2 mt-1">
                              <Tag size="small">{channel.type}</Tag>
                              <span className="text-xs text-gray-400">
                                {channel.memberIds.length} members
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

            <TabPane tab="Users" key="users">
              <List
                dataSource={users}
                renderItem={(user) => (
                  <List.Item className="cursor-pointer hover:bg-gray-50">
                    <List.Item.Meta
                      avatar={
                        <Badge status={getStatusColor(user.status) as any} dot>
                          <Avatar src={user.avatar} icon={<UserOutlined />} />
                        </Badge>
                      }
                      title={
                        <div className="flex justify-between items-center">
                          <span className="font-medium">{user.name}</span>
                          <Tag color={getUserRole(user.role).color} size="small">
                            {getUserRole(user.role).text}
                          </Tag>
                        </div>
                      }
                      description={
                        <div className="text-xs">
                          <div className="capitalize">{user.status}</div>
                          {user.lastSeen && user.status !== 'online' && (
                            <div className="text-gray-400">
                              Last seen {moment(user.lastSeen).fromNow()}
                            </div>
                          )}
                          {user.isTyping && (
                            <div className="text-blue-500">Typing...</div>
                          )}
                        </div>
                      }
                    />
                  </List.Item>
                )}
              />
            </TabPane>

            <TabPane tab="Calls" key="calls">
              <List
                dataSource={videoCalls}
                renderItem={(call) => (
                  <List.Item>
                    <List.Item.Meta
                      avatar={<Avatar icon={<VideoCameraOutlined />} />}
                      title={call.title}
                      description={
                        <div>
                          <div className="text-xs">
                            {moment(call.scheduledTime).format('MMM DD, HH:mm')}
                          </div>
                          <div className="flex items-center gap-2 mt-1">
                            <Tag
                              color={
                                call.status === 'ongoing' ? 'green' :
                                call.status === 'scheduled' ? 'blue' :
                                call.status === 'completed' ? 'gray' : 'red'
                              }
                            >
                              {call.status}
                            </Tag>
                            <span className="text-xs text-gray-400">
                              {call.participants.length} participants
                            </span>
                          </div>
                        </div>
                      }
                    />
                    {call.status === 'scheduled' && (
                      <Button
                        size="small"
                        type="primary"
                        icon={<VideoCameraOutlined />}
                        onClick={() => window.open(call.meetingLink, '_blank')}
                      >
                        Join
                      </Button>
                    )}
                  </List.Item>
                )}
              />
            </TabPane>
          </Tabs>
        </div>

        {/* Main Chat Area */}
        <div className="flex-1 flex flex-col">
          {activeChannel ? (
            <>
              {/* Chat Header */}
              <div className="bg-white border-b px-6 py-4">
                <div className="flex justify-between items-center">
                  <div>
                    <h2 className="text-lg font-semibold">{activeChannel.name}</h2>
                    <p className="text-sm text-gray-600">{activeChannel.description}</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Tooltip title="Start Video Call">
                      <Button
                        icon={<VideoCameraOutlined />}
                        onClick={() => {
                          socket?.initiateCall(activeChannel.memberIds, activeChannel.id);
                        }}
                        disabled={!activeChannel.settings.allowVideoCalls}
                      />
                    </Tooltip>
                    <Tooltip title="Channel Settings">
                      <Button icon={<SettingOutlined />} />
                    </Tooltip>
                    <Tooltip title="Search Messages">
                      <Button icon={<SearchOutlined />} />
                    </Tooltip>
                  </div>
                </div>
              </div>

              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-6 space-y-4">
                <AnimatePresence>
                  {currentChannelMessages.map((message) => {
                    const sender = users.find(u => u.id === message.senderId);
                    const isOwn = message.senderId === 'current_user';

                    return (
                      <motion.div
                        key={message.id}
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        className={`flex ${isOwn ? 'justify-end' : 'justify-start'}`}
                      >
                        <div className={`max-w-lg ${isOwn ? 'order-2' : 'order-1'}`}>
                          {!isOwn && (
                            <div className="flex items-center gap-2 mb-1">
                              <Avatar
                                size="small"
                                src={sender?.avatar}
                                icon={<UserOutlined />}
                              />
                              <span className="text-sm font-medium text-gray-900">
                                {sender?.name}
                              </span>
                              <span className="text-xs text-gray-500">
                                {moment(message.timestamp).format('HH:mm')}
                              </span>
                            </div>
                          )}

                          <div
                            className={`rounded-lg px-4 py-2 ${
                              isOwn
                                ? 'bg-blue-600 text-white'
                                : 'bg-gray-100 text-gray-900'
                            }`}
                          >
                            <div>{message.content}</div>

                            {message.attachments && message.attachments.length > 0 && (
                              <div className="mt-2 space-y-1">
                                {message.attachments.map((attachment, index) => (
                                  <div
                                    key={index}
                                    className="flex items-center gap-2 text-sm"
                                  >
                                    <PaperClipOutlined />
                                    <span>{attachment.name}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>

                          {/* Message Actions */}
                          <div className="flex items-center gap-2 mt-1">
                            {isOwn && (
                              <span className="text-xs text-gray-500">
                                {moment(message.timestamp).format('HH:mm')}
                              </span>
                            )}

                            {autoTranslate && !isOwn && (
                              <Button
                                type="link"
                                size="small"
                                icon={<TranslationOutlined />}
                                onClick={() => translateMessage(message.id, selectedLanguage)}
                              >
                                Translate
                              </Button>
                            )}

                            <Dropdown
                              menu={{
                                items: [
                                  {
                                    key: 'reply',
                                    icon: <MessageOutlined />,
                                    label: 'Reply',
                                  },
                                  {
                                    key: 'forward',
                                    icon: <ShareAltOutlined />,
                                    label: 'Forward',
                                  },
                                  {
                                    key: 'star',
                                    icon: <StarOutlined />,
                                    label: 'Star',
                                  },
                                  ...(isOwn ? [
                                    {
                                      key: 'edit',
                                      icon: <EditOutlined />,
                                      label: 'Edit',
                                    },
                                    {
                                      key: 'delete',
                                      icon: <DeleteOutlined />,
                                      label: 'Delete',
                                      danger: true,
                                    },
                                  ] : []),
                                ],
                              }}
                              trigger={['hover']}
                            >
                              <Button
                                type="text"
                                size="small"
                                icon={<MoreOutlined />}
                                className="opacity-0 group-hover:opacity-100"
                              />
                            </Dropdown>
                          </div>

                          {/* Read Receipts */}
                          {isOwn && message.readBy.length > 0 && (
                            <div className="text-xs text-gray-500 mt-1">
                              Read by {message.readBy.length} people
                            </div>
                          )}
                        </div>
                      </motion.div>
                    );
                  })}
                </AnimatePresence>

                {/* Typing Indicators */}
                {typingUsers.length > 0 && (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <div className="flex -space-x-1">
                      {typingUsers.map(user => (
                        <Avatar
                          key={user.id}
                          size="small"
                          src={user.avatar}
                          icon={<UserOutlined />}
                        />
                      ))}
                    </div>
                    <span>
                      {typingUsers.map(u => u.name).join(', ')}
                      {typingUsers.length === 1 ? ' is' : ' are'} typing...
                    </span>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Message Input */}
              <div className="bg-white border-t p-4">
                <div className="flex items-end gap-3">
                  <div className="flex-1">
                    <Input.Group compact>
                      <TextArea
                        value={messageInput}
                        onChange={(e) => handleTyping(e.target.value)}
                        onPressEnter={(e) => {
                          if (!e.shiftKey) {
                            e.preventDefault();
                            sendMessage();
                          }
                        }}
                        placeholder="Type your message..."
                        autoSize={{ minRows: 1, maxRows: 4 }}
                        className="resize-none"
                      />
                    </Input.Group>
                  </div>

                  <div className="flex items-center gap-2">
                    <Upload>
                      <Button icon={<PaperClipOutlined />} />
                    </Upload>
                    <Button icon={<SmileOutlined />} />
                    <Button
                      type="primary"
                      icon={<SendOutlined />}
                      onClick={sendMessage}
                      disabled={!messageInput.trim()}
                    >
                      Send
                    </Button>
                  </div>
                </div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <MessageOutlined className="text-6xl text-gray-300 mb-4" />
                <h3 className="text-lg font-semibold text-gray-500">
                  Select a Channel
                </h3>
                <p className="text-gray-400">
                  Choose a channel from the sidebar to start messaging
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Announcements Panel */}
        <div className="w-80 bg-gray-50 border-l flex flex-col">
          <div className="p-4 border-b">
            <h3 className="text-lg font-semibold">Announcements</h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {announcements.map((announcement) => (
              <Card
                key={announcement.id}
                size="small"
                title={
                  <div className="flex items-center gap-2">
                    {announcement.pinned && <BellOutlined className="text-orange-500" />}
                    <span className="text-sm">{announcement.title}</span>
                    <Tag
                      color={
                        announcement.priority === 'urgent' ? 'red' :
                        announcement.priority === 'high' ? 'orange' :
                        announcement.priority === 'medium' ? 'blue' : 'green'
                      }
                      size="small"
                    >
                      {announcement.priority}
                    </Tag>
                  </div>
                }
                extra={
                  <Dropdown
                    menu={{
                      items: [
                        {
                          key: 'mark-read',
                          icon: <CheckCircleOutlined />,
                          label: 'Mark as Read',
                        },
                        {
                          key: 'share',
                          icon: <ShareAltOutlined />,
                          label: 'Share',
                        },
                      ],
                    }}
                  >
                    <Button type="text" size="small" icon={<MoreOutlined />} />
                  </Dropdown>
                }
              >
                <p className="text-sm text-gray-600">{announcement.content}</p>

                <div className="mt-2 text-xs text-gray-500">
                  <div>By {announcement.author}</div>
                  <div>{moment(announcement.createdAt).fromNow()}</div>
                  {announcement.expiresAt && (
                    <div>Expires {moment(announcement.expiresAt).fromNow()}</div>
                  )}
                </div>

                {announcement.readBy.length > 0 && (
                  <div className="mt-2 flex items-center gap-1">
                    <EyeOutlined className="text-gray-400" />
                    <span className="text-xs text-gray-500">
                      Read by {announcement.readBy.length} people
                    </span>
                  </div>
                )}
              </Card>
            ))}

            {announcements.length === 0 && (
              <Empty
                description="No announcements"
                image={Empty.PRESENTED_IMAGE_SIMPLE}
              />
            )}
          </div>
        </div>
      </div>

      {/* Create Channel Modal */}
      <Modal
        title="Create New Channel"
        open={showChannelModal}
        onCancel={() => {
          setShowChannelModal(false);
          channelForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={channelForm}
          layout="vertical"
          onFinish={createChannel}
        >
          <Form.Item
            name="name"
            label="Channel Name"
            rules={[{ required: true, message: 'Please enter channel name' }]}
          >
            <Input placeholder="e.g., General Discussion" />
          </Form.Item>

          <Form.Item
            name="description"
            label="Description"
          >
            <TextArea rows={3} placeholder="Brief description of the channel purpose" />
          </Form.Item>

          <Form.Item
            name="type"
            label="Channel Type"
            rules={[{ required: true, message: 'Please select channel type' }]}
          >
            <Radio.Group>
              <Radio value="public">Public - Anyone can join</Radio>
              <Radio value="private">Private - Invite only</Radio>
              <Radio value="department">Department - Specific group</Radio>
            </Radio.Group>
          </Form.Item>

          <Form.Item label="Settings">
            <div className="space-y-2">
              <Form.Item name="allowFiles" valuePropName="checked" noStyle>
                <Checkbox>Allow file attachments</Checkbox>
              </Form.Item>
              <Form.Item name="allowVideoCalls" valuePropName="checked" noStyle>
                <Checkbox>Allow video calls</Checkbox>
              </Form.Item>
              <Form.Item name="autoTranslate" valuePropName="checked" noStyle>
                <Checkbox>Enable auto-translation</Checkbox>
              </Form.Item>
            </div>
          </Form.Item>

          <Form.Item
            name="retentionDays"
            label="Message Retention (days)"
            initialValue={30}
          >
            <Select>
              <Option value={7}>7 days</Option>
              <Option value={30}>30 days</Option>
              <Option value={90}>90 days</Option>
              <Option value={365}>1 year</Option>
              <Option value={-1}>Forever</Option>
            </Select>
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowChannelModal(false);
              channelForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Create Channel
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Create Announcement Modal */}
      <Modal
        title="Create Announcement"
        open={showAnnouncementModal}
        onCancel={() => {
          setShowAnnouncementModal(false);
          announcementForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={announcementForm}
          layout="vertical"
          onFinish={createAnnouncement}
        >
          <Form.Item
            name="title"
            label="Title"
            rules={[{ required: true, message: 'Please enter announcement title' }]}
          >
            <Input placeholder="Announcement title" />
          </Form.Item>

          <Form.Item
            name="content"
            label="Content"
            rules={[{ required: true, message: 'Please enter announcement content' }]}
          >
            <TextArea rows={4} placeholder="Announcement content" />
          </Form.Item>

          <Row gutter={16}>
            <Col span={12}>
              <Form.Item
                name="priority"
                label="Priority"
                rules={[{ required: true, message: 'Please select priority' }]}
              >
                <Select>
                  <Option value="low">Low</Option>
                  <Option value="medium">Medium</Option>
                  <Option value="high">High</Option>
                  <Option value="urgent">Urgent</Option>
                </Select>
              </Form.Item>
            </Col>
            <Col span={12}>
              <Form.Item
                name="targetAudience"
                label="Target Audience"
                rules={[{ required: true, message: 'Please select target audience' }]}
              >
                <Select mode="multiple">
                  <Option value="all_users">All Users</Option>
                  <Option value="all_staff">All Staff</Option>
                  <Option value="all_students">All Students</Option>
                  <Option value="all_parents">All Parents</Option>
                  <Option value="teachers">Teachers</Option>
                  <Option value="admins">Administrators</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <Form.Item
            name="expiresAt"
            label="Expires At (Optional)"
          >
            <DatePicker showTime style={{ width: '100%' }} />
          </Form.Item>

          <Form.Item name="pinned" valuePropName="checked">
            <Checkbox>Pin this announcement</Checkbox>
          </Form.Item>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowAnnouncementModal(false);
              announcementForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Create Announcement
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Schedule Call Modal */}
      <Modal
        title="Schedule Video Call"
        open={showCallModal}
        onCancel={() => {
          setShowCallModal(false);
          callForm.resetFields();
        }}
        footer={null}
        width={600}
      >
        <Form
          form={callForm}
          layout="vertical"
          onFinish={scheduleVideoCall}
        >
          <Form.Item
            name="title"
            label="Meeting Title"
            rules={[{ required: true, message: 'Please enter meeting title' }]}
          >
            <Input placeholder="e.g., Weekly Team Meeting" />
          </Form.Item>

          <Form.Item
            name="participants"
            label="Participants"
            rules={[{ required: true, message: 'Please select participants' }]}
          >
            <Select
              mode="multiple"
              placeholder="Select participants"
              options={users.map(user => ({
                label: user.name,
                value: user.id,
              }))}
            />
          </Form.Item>

          <Row gutter={16}>
            <Col span={16}>
              <Form.Item
                name="scheduledTime"
                label="Date & Time"
                rules={[{ required: true, message: 'Please select date and time' }]}
              >
                <DatePicker showTime style={{ width: '100%' }} />
              </Form.Item>
            </Col>
            <Col span={8}>
              <Form.Item
                name="duration"
                label="Duration (minutes)"
                rules={[{ required: true, message: 'Please enter duration' }]}
              >
                <Select>
                  <Option value={15}>15 minutes</Option>
                  <Option value={30}>30 minutes</Option>
                  <Option value={60}>1 hour</Option>
                  <Option value={90}>1.5 hours</Option>
                  <Option value={120}>2 hours</Option>
                </Select>
              </Form.Item>
            </Col>
          </Row>

          <div className="flex justify-end gap-2">
            <Button onClick={() => {
              setShowCallModal(false);
              callForm.resetFields();
            }}>
              Cancel
            </Button>
            <Button type="primary" htmlType="submit">
              Schedule Call
            </Button>
          </div>
        </Form>
      </Modal>

      {/* Settings Drawer */}
      <Drawer
        title="Communication Settings"
        placement="right"
        width={400}
        open={showSettingsDrawer}
        onClose={() => setShowSettingsDrawer(false)}
      >
        <div className="space-y-6">
          <div>
            <h3 className="text-lg font-semibold mb-3">Notifications</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>Push Notifications</span>
                <Switch
                  checked={notificationsEnabled}
                  onChange={setNotificationsEnabled}
                />
              </div>
              <div className="flex justify-between items-center">
                <span>Sound Notifications</span>
                <Switch defaultChecked />
              </div>
              <div className="flex justify-between items-center">
                <span>Email Notifications</span>
                <Switch defaultChecked />
              </div>
            </div>
          </div>

          <Divider />

          <div>
            <h3 className="text-lg font-semibold mb-3">Language & Translation</h3>
            <div className="space-y-3">
              <div>
                <label className="block text-sm font-medium mb-1">
                  Preferred Language
                </label>
                <Select
                  value={selectedLanguage}
                  onChange={setSelectedLanguage}
                  style={{ width: '100%' }}
                >
                  <Option value="en">English</Option>
                  <Option value="es">Español</Option>
                  <Option value="fr">Français</Option>
                  <Option value="de">Deutsch</Option>
                  <Option value="zh">中文</Option>
                </Select>
              </div>
              <div className="flex justify-between items-center">
                <span>Auto-translate messages</span>
                <Switch
                  checked={autoTranslate}
                  onChange={setAutoTranslate}
                />
              </div>
            </div>
          </div>

          <Divider />

          <div>
            <h3 className="text-lg font-semibold mb-3">Privacy</h3>
            <div className="space-y-3">
              <div className="flex justify-between items-center">
                <span>Show online status</span>
                <Switch defaultChecked />
              </div>
              <div className="flex justify-between items-center">
                <span>Read receipts</span>
                <Switch defaultChecked />
              </div>
              <div className="flex justify-between items-center">
                <span>Typing indicators</span>
                <Switch defaultChecked />
              </div>
            </div>
          </div>
        </div>
      </Drawer>
    </div>
  );
};

export default CommunicationHub;