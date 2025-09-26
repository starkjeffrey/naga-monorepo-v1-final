/**
 * Detail Modal Pattern
 *
 * A comprehensive modal component for displaying detailed information:
 * - Tabbed interface with multiple sections
 * - Real-time data updates
 * - Edit in place functionality
 * - Document management
 * - Timeline view
 * - Action buttons
 * - Responsive design
 */

import React, { useState, useEffect } from 'react';
import {
  Modal,
  Tabs,
  Button,
  Space,
  Avatar,
  Tag,
  Descriptions,
  Card,
  Timeline,
  Upload,
  Form,
  Input,
  Select,
  DatePicker,
  Switch,
  Divider,
  Badge,
  Tooltip,
  Popconfirm,
  message,
  Spin,
} from 'antd';
import {
  EditOutlined,
  SaveOutlined,
  CloseOutlined,
  PlusOutlined,
  DownloadOutlined,
  FileTextOutlined,
  MessageOutlined,
  HistoryOutlined,
  UserOutlined,
  PhoneOutlined,
  MailOutlined,
  HomeOutlined,
  CalendarOutlined,
} from '@ant-design/icons';
import type { UploadFile } from 'antd/es/upload/interface';

const { TabPane } = Tabs;
const { TextArea } = Input;
const { Option } = Select;

export interface DetailTab {
  key: string;
  label: string;
  icon?: React.ReactNode;
  content: React.ReactNode;
  badge?: number | string;
  disabled?: boolean;
}

export interface DetailAction {
  key: string;
  label: string;
  icon?: React.ReactNode;
  type?: 'default' | 'primary' | 'dashed' | 'link' | 'text';
  danger?: boolean;
  loading?: boolean;
  disabled?: boolean;
  onClick: () => void | Promise<void>;
}

export interface DetailModalProps {
  // Modal props
  open: boolean;
  onClose: () => void;
  title: string;
  width?: number;
  destroyOnClose?: boolean;

  // Header
  avatar?: string;
  subtitle?: string;
  status?: {
    text: string;
    color: string;
  };
  badges?: Array<{
    text: string;
    color?: string;
  }>;

  // Tabs
  tabs: DetailTab[];
  defaultActiveTab?: string;
  activeTab?: string;
  onTabChange?: (key: string) => void;

  // Actions
  actions?: DetailAction[];
  primaryAction?: DetailAction;

  // Loading
  loading?: boolean;

  // Data
  data?: any;
  onDataChange?: (data: any) => void;
}

export const DetailModal: React.FC<DetailModalProps> = ({
  open,
  onClose,
  title,
  width = 1200,
  destroyOnClose = true,
  avatar,
  subtitle,
  status,
  badges = [],
  tabs,
  defaultActiveTab,
  activeTab,
  onTabChange,
  actions = [],
  primaryAction,
  loading = false,
  data,
  onDataChange,
}) => {
  const [currentTab, setCurrentTab] = useState(defaultActiveTab || tabs[0]?.key);

  useEffect(() => {
    if (activeTab) {
      setCurrentTab(activeTab);
    }
  }, [activeTab]);

  const handleTabChange = (key: string) => {
    setCurrentTab(key);
    onTabChange?.(key);
  };

  const renderHeader = () => (
    <div className="flex items-start justify-between p-6 pb-0">
      <div className="flex items-start space-x-4">
        {avatar && (
          <Avatar size={64} src={avatar} icon={<UserOutlined />} />
        )}
        <div className="flex-1">
          <div className="flex items-center space-x-3 mb-2">
            <h2 className="text-xl font-semibold text-gray-900 m-0">{title}</h2>
            {status && (
              <Tag color={status.color}>{status.text}</Tag>
            )}
          </div>
          {subtitle && (
            <p className="text-gray-600 mb-2">{subtitle}</p>
          )}
          {badges.length > 0 && (
            <div className="flex flex-wrap gap-1">
              {badges.map((badge, index) => (
                <Tag key={index} color={badge.color}>
                  {badge.text}
                </Tag>
              ))}
            </div>
          )}
        </div>
      </div>

      {(actions.length > 0 || primaryAction) && (
        <div className="flex items-center space-x-2">
          {actions.map(action => (
            <Button
              key={action.key}
              type={action.type}
              icon={action.icon}
              danger={action.danger}
              loading={action.loading}
              disabled={action.disabled}
              onClick={action.onClick}
            >
              {action.label}
            </Button>
          ))}
          {primaryAction && (
            <Button
              type={primaryAction.type || 'primary'}
              icon={primaryAction.icon}
              danger={primaryAction.danger}
              loading={primaryAction.loading}
              disabled={primaryAction.disabled}
              onClick={primaryAction.onClick}
            >
              {primaryAction.label}
            </Button>
          )}
        </div>
      )}
    </div>
  );

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={null}
      footer={null}
      width={width}
      destroyOnClose={destroyOnClose}
      className="detail-modal"
      styles={{
        body: { padding: 0 },
      }}
    >
      <Spin spinning={loading}>
        {renderHeader()}

        <div className="px-6 pb-6">
          <Tabs
            activeKey={currentTab}
            onChange={handleTabChange}
            items={tabs.map(tab => ({
              key: tab.key,
              label: (
                <span className="flex items-center">
                  {tab.icon}
                  <span className="ml-2">{tab.label}</span>
                  {tab.badge && (
                    <Badge
                      count={tab.badge}
                      size="small"
                      className="ml-2"
                    />
                  )}
                </span>
              ),
              children: tab.content,
              disabled: tab.disabled,
            }))}
          />
        </div>
      </Spin>
    </Modal>
  );
};

// Helper components for common tab content

export interface InfoTabProps {
  data: Record<string, any>;
  editable?: boolean;
  onEdit?: (field: string, value: any) => void;
  fields: Array<{
    key: string;
    label: string;
    type?: 'text' | 'email' | 'phone' | 'date' | 'select' | 'switch';
    options?: Array<{ label: string; value: any }>;
    render?: (value: any) => React.ReactNode;
    editable?: boolean;
  }>;
}

export const InfoTab: React.FC<InfoTabProps> = ({
  data,
  editable = false,
  onEdit,
  fields,
}) => {
  const [editingField, setEditingField] = useState<string | null>(null);
  const [editValue, setEditValue] = useState<any>(null);

  const handleEdit = (field: string, currentValue: any) => {
    setEditingField(field);
    setEditValue(currentValue);
  };

  const handleSave = () => {
    if (editingField) {
      onEdit?.(editingField, editValue);
      setEditingField(null);
      setEditValue(null);
    }
  };

  const handleCancel = () => {
    setEditingField(null);
    setEditValue(null);
  };

  return (
    <Card>
      <Descriptions column={2} bordered>
        {fields.map(field => (
          <Descriptions.Item key={field.key} label={field.label}>
            {editingField === field.key ? (
              <div className="flex items-center space-x-2">
                {field.type === 'select' ? (
                  <Select
                    value={editValue}
                    onChange={setEditValue}
                    style={{ minWidth: 120 }}
                  >
                    {field.options?.map(option => (
                      <Option key={option.value} value={option.value}>
                        {option.label}
                      </Option>
                    ))}
                  </Select>
                ) : field.type === 'switch' ? (
                  <Switch
                    checked={editValue}
                    onChange={setEditValue}
                  />
                ) : field.type === 'date' ? (
                  <DatePicker
                    value={editValue}
                    onChange={setEditValue}
                  />
                ) : (
                  <Input
                    value={editValue}
                    onChange={(e) => setEditValue(e.target.value)}
                    type={field.type === 'email' ? 'email' : 'text'}
                  />
                )}
                <Button
                  type="primary"
                  size="small"
                  icon={<SaveOutlined />}
                  onClick={handleSave}
                />
                <Button
                  size="small"
                  icon={<CloseOutlined />}
                  onClick={handleCancel}
                />
              </div>
            ) : (
              <div className="flex items-center justify-between">
                <span>
                  {field.render
                    ? field.render(data[field.key])
                    : data[field.key] || '-'
                  }
                </span>
                {editable && field.editable !== false && (
                  <Button
                    type="link"
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => handleEdit(field.key, data[field.key])}
                  />
                )}
              </div>
            )}
          </Descriptions.Item>
        ))}
      </Descriptions>
    </Card>
  );
};

export interface TimelineTabProps {
  events: Array<{
    id: string;
    timestamp: string;
    title: string;
    description?: string;
    type?: 'default' | 'success' | 'error' | 'warning';
    icon?: React.ReactNode;
    user?: string;
  }>;
  loading?: boolean;
}

export const TimelineTab: React.FC<TimelineTabProps> = ({
  events,
  loading = false,
}) => (
  <Card>
    <Spin spinning={loading}>
      <Timeline>
        {events.map(event => (
          <Timeline.Item
            key={event.id}
            color={
              event.type === 'success' ? 'green' :
              event.type === 'error' ? 'red' :
              event.type === 'warning' ? 'orange' :
              'blue'
            }
            dot={event.icon}
          >
            <div className="flex justify-between items-start mb-1">
              <h4 className="text-sm font-medium">{event.title}</h4>
              <span className="text-xs text-gray-500">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
            {event.description && (
              <p className="text-sm text-gray-600 mb-1">{event.description}</p>
            )}
            {event.user && (
              <span className="text-xs text-gray-500">by {event.user}</span>
            )}
          </Timeline.Item>
        ))}
      </Timeline>
    </Spin>
  </Card>
);

export interface DocumentsTabProps {
  documents: Array<{
    id: string;
    name: string;
    type: string;
    size: number;
    uploadDate: string;
    url: string;
  }>;
  onUpload?: (files: UploadFile[]) => void;
  onDownload?: (document: any) => void;
  onDelete?: (documentId: string) => void;
  loading?: boolean;
}

export const DocumentsTab: React.FC<DocumentsTabProps> = ({
  documents,
  onUpload,
  onDownload,
  onDelete,
  loading = false,
}) => (
  <Card>
    <div className="mb-4">
      {onUpload && (
        <Upload
          multiple
          showUploadList={false}
          beforeUpload={() => false}
          onChange={(info) => onUpload(info.fileList)}
        >
          <Button icon={<PlusOutlined />} type="dashed">
            Upload Document
          </Button>
        </Upload>
      )}
    </div>

    <Spin spinning={loading}>
      <div className="space-y-3">
        {documents.map(doc => (
          <div
            key={doc.id}
            className="flex items-center justify-between p-3 border rounded-lg"
          >
            <div className="flex items-center space-x-3">
              <FileTextOutlined className="text-blue-500" />
              <div>
                <div className="font-medium">{doc.name}</div>
                <div className="text-sm text-gray-500">
                  {doc.type} • {(doc.size / 1024 / 1024).toFixed(2)} MB • {new Date(doc.uploadDate).toLocaleDateString()}
                </div>
              </div>
            </div>
            <Space>
              {onDownload && (
                <Button
                  type="link"
                  icon={<DownloadOutlined />}
                  onClick={() => onDownload(doc)}
                >
                  Download
                </Button>
              )}
              {onDelete && (
                <Popconfirm
                  title="Delete document?"
                  onConfirm={() => onDelete(doc.id)}
                >
                  <Button type="link" danger>
                    Delete
                  </Button>
                </Popconfirm>
              )}
            </Space>
          </div>
        ))}
      </div>
    </Spin>
  </Card>
);

export default DetailModal;