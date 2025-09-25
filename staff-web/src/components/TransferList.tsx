import React, { useState, useCallback } from 'react';
import { Input, Card, Button, Checkbox } from 'antd';
import {
  DoubleRightOutlined,
  RightOutlined,
  LeftOutlined,
  DoubleLeftOutlined,
  SearchOutlined
} from '@ant-design/icons';

export interface TransferItem {
  id: string;
  name: string;
  email?: string;
  studentId?: string;
  [key: string]: any;
}

interface ListPanelProps {
  title: string;
  items: TransferItem[];
  selectedItems: string[];
  onSelectionChange: (selected: string[]) => void;
  searchable?: boolean;
}

const ListPanel: React.FC<ListPanelProps> = ({
  title,
  items,
  selectedItems,
  onSelectionChange,
  searchable = true
}) => {
  const [searchTerm, setSearchTerm] = useState('');

  const filteredItems = items.filter(item =>
    item.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (item.email && item.email.toLowerCase().includes(searchTerm.toLowerCase())) ||
    (item.studentId && item.studentId.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  const handleItemClick = useCallback((itemId: string) => {
    const newSelection = selectedItems.includes(itemId)
      ? selectedItems.filter(id => id !== itemId)
      : [...selectedItems, itemId];
    onSelectionChange(newSelection);
  }, [selectedItems, onSelectionChange]);

  const handleSelectAll = useCallback(() => {
    if (selectedItems.length === filteredItems.length) {
      onSelectionChange([]);
    } else {
      onSelectionChange(filteredItems.map(item => item.id));
    }
  }, [filteredItems, selectedItems.length, onSelectionChange]);

  const allSelected = filteredItems.length > 0 && selectedItems.length === filteredItems.length;

  return (
    <Card
      title={
        <div className="flex justify-between items-center">
          <span>{title}</span>
          <span className="text-sm text-gray-500 font-normal">
            {selectedItems.length}/{filteredItems.length} selected
          </span>
        </div>
      }
      className="h-96 flex flex-col"
      bodyStyle={{ padding: '12px', flex: 1, display: 'flex', flexDirection: 'column' }}
    >
      {searchable && (
        <Input
          placeholder="Search..."
          prefix={<SearchOutlined />}
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          className="mb-3"
          size="small"
        />
      )}

      <Button
        size="small"
        onClick={handleSelectAll}
        className="mb-3 w-full"
      >
        {allSelected ? 'Deselect All' : 'Select All'}
      </Button>

      <div className="flex-1 overflow-y-auto">
        {filteredItems.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500">
            {searchTerm ? 'No items found' : 'No items available'}
          </div>
        ) : (
          <div className="space-y-1">
            {filteredItems.map((item) => (
              <div
                key={item.id}
                onClick={() => handleItemClick(item.id)}
                className={`p-3 rounded-md cursor-pointer transition-colors border ${
                  selectedItems.includes(item.id)
                    ? 'bg-blue-50 border-blue-200 text-blue-900'
                    : 'bg-white border-gray-200 hover:bg-gray-50'
                }`}
              >
                <div className="flex items-center">
                  <Checkbox
                    checked={selectedItems.includes(item.id)}
                    onChange={() => handleItemClick(item.id)}
                    onClick={(e) => e.stopPropagation()}
                    className="mr-3"
                  />
                  <div className="flex-1">
                    <div className="font-medium text-sm">{item.name}</div>
                    {item.email && (
                      <div className="text-xs text-gray-500 mt-1">{item.email}</div>
                    )}
                    {item.studentId && (
                      <div className="text-xs text-gray-500">ID: {item.studentId}</div>
                    )}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
};

export interface TransferListProps {
  availableItems: TransferItem[];
  enrolledItems: TransferItem[];
  availableTitle?: string;
  enrolledTitle?: string;
  searchable?: boolean;
  onChange?: (available: TransferItem[], enrolled: TransferItem[]) => void;
}

export const TransferList: React.FC<TransferListProps> = ({
  availableItems: initialAvailable,
  enrolledItems: initialEnrolled,
  availableTitle = 'Available',
  enrolledTitle = 'Selected',
  searchable = true,
  onChange
}) => {
  const [available, setAvailable] = useState<TransferItem[]>(initialAvailable);
  const [enrolled, setEnrolled] = useState<TransferItem[]>(initialEnrolled);
  const [selectedAvailable, setSelectedAvailable] = useState<string[]>([]);
  const [selectedEnrolled, setSelectedEnrolled] = useState<string[]>([]);

  const handleTransfer = useCallback((newAvailable: TransferItem[], newEnrolled: TransferItem[]) => {
    setAvailable(newAvailable);
    setEnrolled(newEnrolled);
    onChange?.(newAvailable, newEnrolled);
  }, [onChange]);

  const handleEnroll = useCallback(() => {
    const itemsToEnroll = available.filter(item => selectedAvailable.includes(item.id));
    const newAvailable = available.filter(item => !selectedAvailable.includes(item.id));
    const newEnrolled = [...enrolled, ...itemsToEnroll];

    setSelectedAvailable([]);
    handleTransfer(newAvailable, newEnrolled);
  }, [available, enrolled, selectedAvailable, handleTransfer]);

  const handleUnenroll = useCallback(() => {
    const itemsToUnenroll = enrolled.filter(item => selectedEnrolled.includes(item.id));
    const newEnrolled = enrolled.filter(item => !selectedEnrolled.includes(item.id));
    const newAvailable = [...available, ...itemsToUnenroll];

    setSelectedEnrolled([]);
    handleTransfer(newAvailable, newEnrolled);
  }, [available, enrolled, selectedEnrolled, handleTransfer]);

  const handleEnrollAll = useCallback(() => {
    const newEnrolled = [...enrolled, ...available];
    setSelectedAvailable([]);
    handleTransfer([], newEnrolled);
  }, [available, enrolled, handleTransfer]);

  const handleUnenrollAll = useCallback(() => {
    const newAvailable = [...available, ...enrolled];
    setSelectedEnrolled([]);
    handleTransfer(newAvailable, []);
  }, [available, enrolled, handleTransfer]);

  return (
    <div className="flex flex-col lg:flex-row gap-4 w-full max-w-6xl mx-auto">
      {/* Available Items List */}
      <div className="flex-1">
        <ListPanel
          title={availableTitle}
          items={available}
          selectedItems={selectedAvailable}
          onSelectionChange={setSelectedAvailable}
          searchable={searchable}
        />
      </div>

      {/* Transfer Controls */}
      <div className="flex lg:flex-col items-center justify-center gap-2 lg:gap-4 py-4">
        <div className="flex lg:flex-col gap-2">
          <Button
            type="default"
            size="large"
            icon={<DoubleRightOutlined />}
            onClick={handleEnrollAll}
            disabled={available.length === 0}
            title="Move all to enrolled"
            className="lg:w-12 lg:h-12"
          />

          <Button
            type="primary"
            size="large"
            icon={<RightOutlined />}
            onClick={handleEnroll}
            disabled={selectedAvailable.length === 0}
            title="Move selected to enrolled"
            className="lg:w-12 lg:h-12"
          />

          <Button
            type="primary"
            size="large"
            icon={<LeftOutlined />}
            onClick={handleUnenroll}
            disabled={selectedEnrolled.length === 0}
            title="Move selected to available"
            className="lg:w-12 lg:h-12"
          />

          <Button
            type="default"
            size="large"
            icon={<DoubleLeftOutlined />}
            onClick={handleUnenrollAll}
            disabled={enrolled.length === 0}
            title="Move all to available"
            className="lg:w-12 lg:h-12"
          />
        </div>
      </div>

      {/* Enrolled Items List */}
      <div className="flex-1">
        <ListPanel
          title={enrolledTitle}
          items={enrolled}
          selectedItems={selectedEnrolled}
          onSelectionChange={setSelectedEnrolled}
          searchable={searchable}
        />
      </div>
    </div>
  );
};

export default TransferList;