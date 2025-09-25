import React, { useState } from 'react';
import { Card, Typography, Space, Tag, Divider } from 'antd';
import TransferList, { TransferItem } from '../../components/TransferList';

const { Title, Paragraph } = Typography;

// Sample data for different scenarios
const sampleStudents: TransferItem[] = [
  { id: '1', name: 'Alice Johnson', email: 'alice@example.com', studentId: 'ST001' },
  { id: '2', name: 'Bob Smith', email: 'bob@example.com', studentId: 'ST002' },
  { id: '3', name: 'Charlie Brown', email: 'charlie@example.com', studentId: 'ST003' },
  { id: '4', name: 'Diana Prince', email: 'diana@example.com', studentId: 'ST004' },
  { id: '5', name: 'Edward Norton', email: 'edward@example.com', studentId: 'ST005' },
  { id: '6', name: 'Fiona Green', email: 'fiona@example.com', studentId: 'ST006' },
  { id: '7', name: 'George Wilson', email: 'george@example.com', studentId: 'ST007' },
  { id: '8', name: 'Hannah Davis', email: 'hannah@example.com', studentId: 'ST008' },
];

const sampleEnrolled: TransferItem[] = [
  { id: '9', name: 'Ian Thompson', email: 'ian@example.com', studentId: 'ST009' },
  { id: '10', name: 'Julia Roberts', email: 'julia@example.com', studentId: 'ST010' },
];

const samplePermissions: TransferItem[] = [
  { id: 'p1', name: 'View Reports', email: 'Access to all reports' },
  { id: 'p2', name: 'Edit Students', email: 'Create and modify student records' },
  { id: 'p3', name: 'Manage Grades', email: 'Enter and modify grades' },
  { id: 'p4', name: 'Financial Access', email: 'View and manage financial records' },
  { id: 'p5', name: 'System Admin', email: 'Full system administration' },
];

const sampleUserPermissions: TransferItem[] = [
  { id: 'p6', name: 'View Students', email: 'Basic student viewing access' },
];

export const TransferListDemo: React.FC = () => {
  const [studentCounts, setStudentCounts] = useState({ available: 8, enrolled: 2 });
  const [permissionCounts, setPermissionCounts] = useState({ available: 5, enrolled: 1 });

  const handleStudentTransfer = (available: TransferItem[], enrolled: TransferItem[]) => {
    setStudentCounts({ available: available.length, enrolled: enrolled.length });
    console.log('Student Transfer:', { available: available.length, enrolled: enrolled.length });
  };

  const handlePermissionTransfer = (available: TransferItem[], enrolled: TransferItem[]) => {
    setPermissionCounts({ available: available.length, enrolled: enrolled.length });
    console.log('Permission Transfer:', { available: available.length, enrolled: enrolled.length });
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="text-center mb-8">
          <Title level={1}>TransferList Component Demo</Title>
          <Paragraph className="text-lg text-gray-600">
            A reusable dual-list transfer component for managing relationships between items.
            Perfect for enrollment management, permission assignment, group membership, and more.
          </Paragraph>
        </div>

        {/* Features */}
        <Card className="mb-8">
          <Title level={3}>Key Features</Title>
          <Space wrap>
            <Tag color="blue">Clean Arrow Controls</Tag>
            <Tag color="green">Multi-Selection</Tag>
            <Tag color="orange">Search Functionality</Tag>
            <Tag color="purple">Responsive Design</Tag>
            <Tag color="cyan">TypeScript Support</Tag>
            <Tag color="red">Ant Design Integration</Tag>
          </Space>
        </Card>

        {/* Student Enrollment Demo */}
        <Card className="mb-8">
          <Title level={2}>Student Enrollment Management</Title>
          <Paragraph>
            Manage student enrollment in classes or programs.
            Current: <strong>{studentCounts.available} available</strong> | <strong>{studentCounts.enrolled} enrolled</strong>
          </Paragraph>

          <TransferList
            availableItems={sampleStudents}
            enrolledItems={sampleEnrolled}
            availableTitle="Available Students"
            enrolledTitle="Enrolled Students"
            onChange={handleStudentTransfer}
          />
        </Card>

        <Divider />

        {/* Permission Management Demo */}
        <Card className="mb-8">
          <Title level={2}>Permission Management</Title>
          <Paragraph>
            Assign permissions to users or roles.
            Current: <strong>{permissionCounts.available} available</strong> | <strong>{permissionCounts.enrolled} assigned</strong>
          </Paragraph>

          <TransferList
            availableItems={samplePermissions}
            enrolledItems={sampleUserPermissions}
            availableTitle="Available Permissions"
            enrolledTitle="User Permissions"
            onChange={handlePermissionTransfer}
          />
        </Card>

        {/* Usage Instructions */}
        <Card>
          <Title level={3}>How to Use</Title>
          <div className="space-y-4">
            <div>
              <strong>Arrow Controls:</strong>
              <ul className="list-disc ml-6 mt-2">
                <li><strong>&gt;&gt;</strong> Move ALL items from left to right</li>
                <li><strong>&gt;</strong> Move SELECTED items from left to right</li>
                <li><strong>&lt;</strong> Move SELECTED items from right to left</li>
                <li><strong>&lt;&lt;</strong> Move ALL items from right to left</li>
              </ul>
            </div>
            <div>
              <strong>Selection:</strong>
              <ul className="list-disc ml-6 mt-2">
                <li>Click items to select/deselect them</li>
                <li>Use checkboxes for multiple selection</li>
                <li>Use "Select All" / "Deselect All" buttons</li>
              </ul>
            </div>
            <div>
              <strong>Search:</strong>
              <ul className="list-disc ml-6 mt-2">
                <li>Search by name, email, or student ID</li>
                <li>Search works independently in each list</li>
              </ul>
            </div>
          </div>
        </Card>
      </div>
    </div>
  );
};

export default TransferListDemo;