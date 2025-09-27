/**
 * StudentTimeline Component
 *
 * A comprehensive timeline component showing student activities and events:
 * - Academic milestones
 * - Enrollment history
 * - Communication logs
 * - Financial transactions
 * - System activities
 * - Real-time updates
 */

import React, { useState, useEffect } from 'react';
import { Timeline, Card, Tag, Button, Space, Tooltip, Badge, Avatar } from 'antd';
import {
  BookOutlined,
  DollarOutlined,
  MessageOutlined,
  UserOutlined,
  CalendarOutlined,
  FileTextOutlined,
  CreditCardOutlined,
  GraduationCapOutlined,
  AlertOutlined,
  PhoneOutlined,
  MailOutlined,
  EditOutlined,
  StarOutlined,
  TrophyOutlined,
  ExclamationCircleOutlined,
} from '@ant-design/icons';
import type { Student, StudentEvent } from '../types/Student';

interface StudentTimelineProps {
  student: Student;
  events?: StudentEvent[];
  showFilters?: boolean;
  realTime?: boolean;
  maxEvents?: number;
  className?: string;
}

const getEventIcon = (type: string) => {
  const iconMap: Record<string, React.ReactNode> = {
    enrollment: <UserOutlined className="text-blue-500" />,
    academic: <BookOutlined className="text-green-500" />,
    financial: <DollarOutlined className="text-orange-500" />,
    communication: <MessageOutlined className="text-purple-500" />,
    document: <FileTextOutlined className="text-gray-500" />,
    payment: <CreditCardOutlined className="text-green-600" />,
    graduation: <GraduationCapOutlined className="text-blue-600" />,
    alert: <AlertOutlined className="text-red-500" />,
    call: <PhoneOutlined className="text-blue-400" />,
    email: <MailOutlined className="text-indigo-500" />,
    edit: <EditOutlined className="text-gray-600" />,
    achievement: <TrophyOutlined className="text-yellow-500" />,
    grade: <StarOutlined className="text-green-500" />,
    warning: <ExclamationCircleOutlined className="text-orange-500" />,
  };
  return iconMap[type] || <CalendarOutlined className="text-gray-400" />;
};

const getEventColor = (type: string, priority?: string) => {
  if (priority === 'high') return 'red';
  if (priority === 'medium') return 'orange';

  const colorMap: Record<string, string> = {
    enrollment: 'blue',
    academic: 'green',
    financial: 'orange',
    communication: 'purple',
    document: 'gray',
    payment: 'green',
    graduation: 'blue',
    alert: 'red',
    achievement: 'gold',
    grade: 'green',
    warning: 'orange',
  };
  return colorMap[type] || 'blue';
};

const formatEventDate = (date: string | Date) => {
  const eventDate = new Date(date);
  const now = new Date();
  const diff = now.getTime() - eventDate.getTime();

  if (diff < 60000) return 'Just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)} minutes ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
  if (diff < 604800000) return `${Math.floor(diff / 86400000)} days ago`;

  return eventDate.toLocaleDateString();
};

const StudentTimeline: React.FC<StudentTimelineProps> = ({
  student,
  events = [],
  showFilters = true,
  realTime = false,
  maxEvents = 50,
  className,
}) => {
  const [filteredEvents, setFilteredEvents] = useState<StudentEvent[]>(events);
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);
  const [expandedEvents, setExpandedEvents] = useState<Set<string>>(new Set());

  useEffect(() => {
    let filtered = [...events];

    if (selectedTypes.length > 0) {
      filtered = filtered.filter(event => selectedTypes.includes(event.type));
    }

    // Sort by date (most recent first)
    filtered.sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime());

    // Limit number of events
    if (maxEvents > 0) {
      filtered = filtered.slice(0, maxEvents);
    }

    setFilteredEvents(filtered);
  }, [events, selectedTypes, maxEvents]);

  const eventTypes = Array.from(new Set(events.map(event => event.type)));

  const toggleEventExpansion = (eventId: string) => {
    const newExpanded = new Set(expandedEvents);
    if (newExpanded.has(eventId)) {
      newExpanded.delete(eventId);
    } else {
      newExpanded.add(eventId);
    }
    setExpandedEvents(newExpanded);
  };

  const filterButtons = showFilters && (
    <div className="mb-4 flex flex-wrap gap-2">
      <Button
        size="small"
        type={selectedTypes.length === 0 ? 'primary' : 'default'}
        onClick={() => setSelectedTypes([])}
      >
        All Events
      </Button>
      {eventTypes.map(type => (
        <Button
          key={type}
          size="small"
          type={selectedTypes.includes(type) ? 'primary' : 'default'}
          onClick={() => {
            setSelectedTypes(prev =>
              prev.includes(type)
                ? prev.filter(t => t !== type)
                : [...prev, type]
            );
          }}
        >
          {type.charAt(0).toUpperCase() + type.slice(1)}
        </Button>
      ))}
    </div>
  );

  const timelineItems = filteredEvents.map(event => {
    const isExpanded = expandedEvents.has(event.id);

    return {
      color: getEventColor(event.type, event.priority),
      dot: getEventIcon(event.type),
      children: (
        <Card
          size="small"
          className="mb-2 hover:shadow-md transition-shadow"
          actions={event.details && [
            <Button
              key="toggle"
              type="link"
              size="small"
              onClick={() => toggleEventExpansion(event.id)}
            >
              {isExpanded ? 'Show Less' : 'Show More'}
            </Button>
          ]}
        >
          <div className="flex items-start justify-between">
            <div className="flex-1">
              <div className="flex items-center space-x-2 mb-1">
                <span className="font-medium">{event.title}</span>
                {event.priority && (
                  <Tag color={getEventColor(event.type, event.priority)} size="small">
                    {event.priority.toUpperCase()}
                  </Tag>
                )}
                {event.automated && (
                  <Tag color="cyan" size="small">AUTO</Tag>
                )}
              </div>

              <div className="text-sm text-gray-600 mb-1">
                {event.description}
              </div>

              <div className="flex items-center space-x-4 text-xs text-gray-500">
                <span>{formatEventDate(event.timestamp)}</span>
                {event.actor && (
                  <span>
                    by {event.actor.name}
                    {event.actor.avatar && (
                      <Avatar
                        size={16}
                        src={event.actor.avatar}
                        className="ml-1"
                      />
                    )}
                  </span>
                )}
                {event.category && (
                  <Tag size="small">{event.category}</Tag>
                )}
              </div>

              {isExpanded && event.details && (
                <div className="mt-3 p-3 bg-gray-50 rounded">
                  <div className="text-sm space-y-2">
                    {typeof event.details === 'string' ? (
                      <p>{event.details}</p>
                    ) : (
                      Object.entries(event.details).map(([key, value]) => (
                        <div key={key} className="flex justify-between">
                          <span className="font-medium">{key}:</span>
                          <span>{String(value)}</span>
                        </div>
                      ))
                    )}
                  </div>
                </div>
              )}

              {event.attachments && event.attachments.length > 0 && (
                <div className="mt-2">
                  <Space size="small" wrap>
                    {event.attachments.map((attachment, index) => (
                      <Button
                        key={index}
                        size="small"
                        type="link"
                        icon={<FileTextOutlined />}
                        onClick={() => window.open(attachment.url, '_blank')}
                      >
                        {attachment.name}
                      </Button>
                    ))}
                  </Space>
                </div>
              )}
            </div>

            {event.status && (
              <Badge
                status={event.status === 'completed' ? 'success' :
                       event.status === 'pending' ? 'processing' :
                       event.status === 'failed' ? 'error' : 'default'}
                text={event.status}
              />
            )}
          </div>
        </Card>
      ),
    };
  });

  if (filteredEvents.length === 0) {
    return (
      <div className={`student-timeline ${className || ''}`}>
        {filterButtons}
        <div className="text-center text-gray-500 py-8">
          <CalendarOutlined className="text-4xl mb-2" />
          <div>No events found</div>
          <div className="text-sm">
            {selectedTypes.length > 0
              ? 'Try adjusting your filters'
              : 'Events will appear here as they occur'
            }
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`student-timeline ${className || ''}`}>
      {filterButtons}

      <div className="mb-4 p-3 bg-blue-50 rounded border border-blue-200">
        <div className="flex items-center justify-between">
          <div>
            <div className="font-medium text-blue-900">
              {filteredEvents.length} Events
            </div>
            <div className="text-sm text-blue-700">
              Showing activity for {student.fullName}
            </div>
          </div>
          {realTime && (
            <Badge status="processing" text="Live Updates" />
          )}
        </div>
      </div>

      <Timeline
        mode="left"
        items={timelineItems}
        className="custom-timeline"
      />

      {events.length > maxEvents && (
        <div className="text-center mt-4">
          <Button type="link">
            Load More Events ({events.length - maxEvents} remaining)
          </Button>
        </div>
      )}
    </div>
  );
};

export default StudentTimeline;