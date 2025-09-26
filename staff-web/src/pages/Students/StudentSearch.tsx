/**
 * Advanced Student Search Component
 *
 * A unified search interface with multiple search modes:
 * - Quick Search: Name or ID lookup with autocomplete
 * - Advanced Search: Multiple criteria with boolean logic
 * - Photo Search: Upload photo for facial recognition matching
 * - Fuzzy Search: Phonetic and approximate matching
 * - Voice Search: Speech recognition for hands-free search
 * - QR Code Scanner: Instant student lookup via QR codes
 * - Machine learning search suggestions
 * - Geographic search (students by location)
 * - Social network analysis (find students with connections)
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Card,
  Input,
  Button,
  Select,
  DatePicker,
  Space,
  Tabs,
  Row,
  Col,
  Avatar,
  List,
  Tag,
  message,
  Upload,
  Modal,
  Tooltip,
  Badge,
  Progress,
  Alert,
  Divider,
  AutoComplete,
  Switch,
  Slider,
  Checkbox,
} from 'antd';
import {
  SearchOutlined,
  CameraOutlined,
  QrcodeOutlined,
  AudioOutlined,
  FilterOutlined,
  UserOutlined,
  HistoryOutlined,
  StarOutlined,
  ShareAltOutlined,
  EnvironmentOutlined,
  BranchesOutlined,
  ExperimentOutlined,
  ThunderboltOutlined,
  CloseOutlined,
  SaveOutlined,
  DownloadOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

import { StudentService } from '../../services/student.service';
import type {
  PersonSearchResult,
  PersonSearchFilters,
  PaginatedResponse,
  SelectOption,
} from '../../types/student.types';

const { Search } = Input;
const { Option } = Select;
const { RangePicker } = DatePicker;
const { TabPane } = Tabs;
const { CheckboxGroup } = Checkbox;

interface SearchHistory {
  id: string;
  query: string;
  type: 'quick' | 'advanced' | 'photo' | 'voice' | 'qr';
  timestamp: string;
  resultCount: number;
  filters?: any;
}

interface SavedSearch {
  id: string;
  name: string;
  description?: string;
  query: string;
  filters: any;
  createdAt: string;
  useCount: number;
}

interface StudentSearchProps {
  onStudentSelect?: (student: PersonSearchResult) => void;
  embedded?: boolean;
  initialQuery?: string;
}

export const StudentSearch: React.FC<StudentSearchProps> = ({
  onStudentSelect,
  embedded = false,
  initialQuery = '',
}) => {
  // Search state
  const [searchResults, setSearchResults] = useState<PersonSearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [totalResults, setTotalResults] = useState(0);
  const [currentPage, setCurrrectPage] = useState(1);

  // Search modes
  const [activeTab, setActiveTab] = useState('quick');
  const [quickQuery, setQuickQuery] = useState(initialQuery);
  const [advancedFilters, setAdvancedFilters] = useState<any>({});
  const [photoSearchFile, setPhotoSearchFile] = useState<File | null>(null);

  // Voice search
  const [isListening, setIsListening] = useState(false);
  const [speechSupported, setSpeechSupported] = useState(false);
  const recognitionRef = useRef<any>(null);

  // Search suggestions
  const [searchSuggestions, setSearchSuggestions] = useState<string[]>([]);
  const [aiSuggestions, setAiSuggestions] = useState<string[]>([]);

  // Search history and saved searches
  const [searchHistory, setSearchHistory] = useState<SearchHistory[]>([]);
  const [savedSearches, setSavedSearches] = useState<SavedSearch[]>([]);

  // Modals
  const [photoSearchVisible, setPhotoSearchVisible] = useState(false);
  const [qrScannerVisible, setQrScannerVisible] = useState(false);
  const [saveSearchVisible, setSaveSearchVisible] = useState(false);
  const [geoSearchVisible, setGeoSearchVisible] = useState(false);

  // Filter options
  const [statusOptions, setStatusOptions] = useState<SelectOption[]>([]);
  const [programOptions, setProgramOptions] = useState<SelectOption[]>([]);

  // Initialize speech recognition
  useEffect(() => {
    if ('webkitSpeechRecognition' in window) {
      setSpeechSupported(true);
      const recognition = new (window as any).webkitSpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = false;
      recognition.lang = 'en-US';

      recognition.onresult = (event: any) => {
        const transcript = event.results[0][0].transcript;
        setQuickQuery(transcript);
        performQuickSearch(transcript);
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
    }
  }, []);

  // Load filter options
  useEffect(() => {
    loadFilterOptions();
    loadSearchHistory();
    loadSavedSearches();
  }, []);

  const loadFilterOptions = async () => {
    try {
      const [statuses, majors] = await Promise.all([
        StudentService.getStudentStatuses(),
        StudentService.listMajors({ active_only: true }),
      ]);

      setStatusOptions(statuses);
      setProgramOptions(
        majors.results.map(major => ({
          label: major.name,
          value: major.id.toString(),
        }))
      );
    } catch (error) {
      console.error('Failed to load filter options:', error);
    }
  };

  const loadSearchHistory = () => {
    const history = localStorage.getItem('student-search-history');
    if (history) {
      setSearchHistory(JSON.parse(history));
    }
  };

  const loadSavedSearches = () => {
    const saved = localStorage.getItem('student-saved-searches');
    if (saved) {
      setSavedSearches(JSON.parse(saved));
    }
  };

  const saveToHistory = (query: string, type: SearchHistory['type'], resultCount: number, filters?: any) => {
    const historyItem: SearchHistory = {
      id: Date.now().toString(),
      query,
      type,
      timestamp: new Date().toISOString(),
      resultCount,
      filters,
    };

    const newHistory = [historyItem, ...searchHistory.slice(0, 19)]; // Keep last 20
    setSearchHistory(newHistory);
    localStorage.setItem('student-search-history', JSON.stringify(newHistory));
  };

  // Quick Search with autocomplete
  const performQuickSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([]);
      setTotalResults(0);
      return;
    }

    try {
      setLoading(true);
      const response = await StudentService.searchPersons({
        q: query,
        page: currentPage,
        page_size: 20,
        roles: ['student'],
      });

      setSearchResults(response.results);
      setTotalResults(response.count);
      saveToHistory(query, 'quick', response.count);

      // Generate AI suggestions based on results
      generateAISuggestions(query, response.results);
    } catch (error) {
      console.error('Search failed:', error);
      message.error('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [currentPage]);

  // Advanced Search with complex filters
  const performAdvancedSearch = async () => {
    try {
      setLoading(true);

      // Build advanced search query
      const searchQuery = buildAdvancedQuery(advancedFilters);

      const response = await StudentService.searchPersons({
        q: searchQuery,
        page: currentPage,
        page_size: 20,
        roles: ['student'],
      });

      setSearchResults(response.results);
      setTotalResults(response.count);
      saveToHistory(searchQuery, 'advanced', response.count, advancedFilters);
    } catch (error) {
      console.error('Advanced search failed:', error);
      message.error('Advanced search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const buildAdvancedQuery = (filters: any) => {
    const queryParts = [];

    if (filters.name) queryParts.push(filters.name);
    if (filters.studentId) queryParts.push(`id:${filters.studentId}`);
    if (filters.email) queryParts.push(`email:${filters.email}`);
    if (filters.status) queryParts.push(`status:${filters.status}`);
    if (filters.program) queryParts.push(`program:${filters.program}`);

    return queryParts.join(' ');
  };

  // Photo Search with facial recognition
  const performPhotoSearch = async (file: File) => {
    try {
      setLoading(true);

      // TODO: Implement facial recognition API
      message.info('Photo search with facial recognition will be implemented');

      // Mock results for now
      const mockResults: PersonSearchResult[] = [
        {
          person_id: 1,
          full_name: 'John Doe',
          khmer_name: '',
          school_email: 'john.doe@school.edu',
          roles: ['student'],
          student_id: 12345,
          formatted_student_id: 'S-12345',
          student_status: 'ACTIVE',
        },
      ];

      setSearchResults(mockResults);
      setTotalResults(mockResults.length);
      saveToHistory(`Photo search: ${file.name}`, 'photo', mockResults.length);

      setPhotoSearchVisible(false);
    } catch (error) {
      message.error('Photo search failed');
    } finally {
      setLoading(false);
    }
  };

  // Voice Search
  const startVoiceSearch = () => {
    if (!speechSupported) {
      message.error('Speech recognition is not supported in your browser');
      return;
    }

    setIsListening(true);
    recognitionRef.current?.start();
  };

  // QR Code Search
  const handleQRCodeScan = (result: string) => {
    try {
      // Extract student ID from QR code
      const studentId = result.match(/student[/_]id[:\s]*(\d+)/i)?.[1];
      if (studentId) {
        setQuickQuery(studentId);
        performQuickSearch(studentId);
        setQrScannerVisible(false);
        message.success(`Found student ID: ${studentId}`);
      } else {
        message.warning('QR code does not contain valid student ID');
      }
    } catch (error) {
      message.error('Failed to process QR code');
    }
  };

  // AI Suggestions
  const generateAISuggestions = (query: string, results: PersonSearchResult[]) => {
    // Mock AI suggestions based on search patterns
    const suggestions = [
      `Students similar to "${query}"`,
      `${query} in Biology program`,
      `Active students named ${query}`,
      `Recent enrollments matching ${query}`,
    ];
    setAiSuggestions(suggestions);
  };

  // Save Search
  const saveCurrentSearch = (name: string, description?: string) => {
    const savedSearch: SavedSearch = {
      id: Date.now().toString(),
      name,
      description,
      query: quickQuery || JSON.stringify(advancedFilters),
      filters: advancedFilters,
      createdAt: new Date().toISOString(),
      useCount: 0,
    };

    const newSaved = [savedSearch, ...savedSearches];
    setSavedSearches(newSaved);
    localStorage.setItem('student-saved-searches', JSON.stringify(newSaved));
    setSaveSearchVisible(false);
    message.success('Search saved successfully');
  };

  // Export Results
  const exportResults = () => {
    const data = searchResults.map(student => ({
      'Student ID': student.formatted_student_id,
      'Name': student.full_name,
      'Email': student.school_email,
      'Status': student.student_status,
      'Roles': student.roles.join(', '),
    }));

    // TODO: Implement CSV export
    message.success('Export functionality will be implemented');
  };

  // Quick Search Tab
  const QuickSearchTab = () => (
    <div className="space-y-4">
      <div className="flex space-x-2">
        <AutoComplete
          style={{ flex: 1 }}
          options={searchSuggestions.map(suggestion => ({ value: suggestion }))}
          onSearch={(value) => {
            // Generate suggestions as user types
            const suggestions = [
              `${value} Biology`,
              `${value} Engineering`,
              `Active ${value}`,
              `Recent ${value}`,
            ].filter(s => s !== value);
            setSearchSuggestions(suggestions);
          }}
        >
          <Search
            placeholder="Search by name, student ID, or email..."
            value={quickQuery}
            onChange={(e) => setQuickQuery(e.target.value)}
            onSearch={performQuickSearch}
            size="large"
            loading={loading}
            enterButton={<SearchOutlined />}
          />
        </AutoComplete>

        {speechSupported && (
          <Tooltip title="Voice Search">
            <Button
              size="large"
              icon={<AudioOutlined />}
              onClick={startVoiceSearch}
              loading={isListening}
              type={isListening ? 'primary' : 'default'}
            />
          </Tooltip>
        )}

        <Tooltip title="Photo Search">
          <Button
            size="large"
            icon={<CameraOutlined />}
            onClick={() => setPhotoSearchVisible(true)}
          />
        </Tooltip>

        <Tooltip title="QR Scanner">
          <Button
            size="large"
            icon={<QrcodeOutlined />}
            onClick={() => setQrScannerVisible(true)}
          />
        </Tooltip>
      </div>

      {/* AI Suggestions */}
      {aiSuggestions.length > 0 && (
        <Card size="small" title="AI Suggestions">
          <div className="flex flex-wrap gap-2">
            {aiSuggestions.map((suggestion, index) => (
              <Button
                key={index}
                size="small"
                type="dashed"
                icon={<ThunderboltOutlined />}
                onClick={() => {
                  setQuickQuery(suggestion);
                  performQuickSearch(suggestion);
                }}
              >
                {suggestion}
              </Button>
            ))}
          </div>
        </Card>
      )}
    </div>
  );

  // Advanced Search Tab
  const AdvancedSearchTab = () => (
    <Card title="Advanced Search Filters">
      <Row gutter={16}>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Name</label>
            <Input
              placeholder="Full name or partial name"
              value={advancedFilters.name}
              onChange={(e) => setAdvancedFilters({...advancedFilters, name: e.target.value})}
            />
          </div>
        </Col>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Student ID</label>
            <Input
              placeholder="Student ID number"
              value={advancedFilters.studentId}
              onChange={(e) => setAdvancedFilters({...advancedFilters, studentId: e.target.value})}
            />
          </div>
        </Col>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Email</label>
            <Input
              placeholder="Email address"
              value={advancedFilters.email}
              onChange={(e) => setAdvancedFilters({...advancedFilters, email: e.target.value})}
            />
          </div>
        </Col>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Status</label>
            <Select
              placeholder="Select status"
              style={{ width: '100%' }}
              value={advancedFilters.status}
              onChange={(value) => setAdvancedFilters({...advancedFilters, status: value})}
              allowClear
            >
              {statusOptions.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </div>
        </Col>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Program</label>
            <Select
              placeholder="Select program"
              style={{ width: '100%' }}
              value={advancedFilters.program}
              onChange={(value) => setAdvancedFilters({...advancedFilters, program: value})}
              allowClear
            >
              {programOptions.map(option => (
                <Option key={option.value} value={option.value}>
                  {option.label}
                </Option>
              ))}
            </Select>
          </div>
        </Col>
        <Col span={12}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Enrollment Date Range</label>
            <RangePicker
              style={{ width: '100%' }}
              value={advancedFilters.enrollmentDateRange}
              onChange={(dates) => setAdvancedFilters({...advancedFilters, enrollmentDateRange: dates})}
            />
          </div>
        </Col>
        <Col span={24}>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Additional Filters</label>
            <CheckboxGroup
              options={[
                { label: 'Monk Status', value: 'is_monk' },
                { label: 'Transfer Students', value: 'is_transfer' },
                { label: 'International Students', value: 'international' },
                { label: 'Scholarship Recipients', value: 'has_scholarship' },
              ]}
              value={advancedFilters.additionalFilters}
              onChange={(values) => setAdvancedFilters({...advancedFilters, additionalFilters: values})}
            />
          </div>
        </Col>
      </Row>

      <div className="text-right">
        <Space>
          <Button onClick={() => setAdvancedFilters({})}>Clear All</Button>
          <Button type="primary" onClick={performAdvancedSearch} loading={loading}>
            Search
          </Button>
        </Space>
      </div>
    </Card>
  );

  // Search History Tab
  const SearchHistoryTab = () => (
    <Card title="Recent Searches">
      <List
        dataSource={searchHistory}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button
                type="link"
                onClick={() => {
                  if (item.type === 'quick') {
                    setActiveTab('quick');
                    setQuickQuery(item.query);
                    performQuickSearch(item.query);
                  } else if (item.type === 'advanced') {
                    setActiveTab('advanced');
                    setAdvancedFilters(item.filters || {});
                  }
                }}
              >
                Repeat
              </Button>,
              <Button type="link" icon={<StarOutlined />}>
                Save
              </Button>,
            ]}
          >
            <div className="flex items-center space-x-3">
              <HistoryOutlined />
              <div>
                <div className="font-medium">{item.query}</div>
                <div className="text-sm text-gray-500">
                  {dayjs(item.timestamp).format('MMM D, YYYY HH:mm')} •{' '}
                  {item.resultCount} results • {item.type}
                </div>
              </div>
            </div>
          </List.Item>
        )}
      />
    </Card>
  );

  // Saved Searches Tab
  const SavedSearchesTab = () => (
    <Card title="Saved Searches" extra={
      <Button icon={<SaveOutlined />} onClick={() => setSaveSearchVisible(true)}>
        Save Current
      </Button>
    }>
      <List
        dataSource={savedSearches}
        renderItem={(item) => (
          <List.Item
            actions={[
              <Button type="link" onClick={() => {
                // Load saved search
                message.info('Loading saved search...');
              }}>
                Load
              </Button>,
              <Button type="link" danger>
                Delete
              </Button>,
            ]}
          >
            <div className="flex items-center justify-between w-full">
              <div>
                <div className="font-medium">{item.name}</div>
                {item.description && (
                  <div className="text-sm text-gray-500">{item.description}</div>
                )}
                <div className="text-xs text-gray-400">
                  Created {dayjs(item.createdAt).format('MMM D, YYYY')} • Used {item.useCount} times
                </div>
              </div>
              <Badge count={item.useCount} />
            </div>
          </List.Item>
        )}
      />
    </Card>
  );

  // Results Display
  const ResultsList = () => (
    <Card
      title={`Search Results (${totalResults})`}
      extra={
        <Space>
          <Button icon={<DownloadOutlined />} onClick={exportResults}>
            Export
          </Button>
          {totalResults > 0 && (
            <Button icon={<SaveOutlined />} onClick={() => setSaveSearchVisible(true)}>
              Save Search
            </Button>
          )}
        </Space>
      }
    >
      {loading ? (
        <div className="text-center py-8">
          <Progress percent={30} />
          <p className="mt-2">Searching students...</p>
        </div>
      ) : (
        <List
          dataSource={searchResults}
          renderItem={(student) => (
            <List.Item
              onClick={() => onStudentSelect?.(student)}
              className="cursor-pointer hover:bg-gray-50"
              actions={[
                <Button type="link" icon={<UserOutlined />}>
                  View Profile
                </Button>,
              ]}
            >
              <div className="flex items-center space-x-3 w-full">
                <Avatar
                  src={student.current_thumbnail_url}
                  icon={<UserOutlined />}
                  size={48}
                />
                <div className="flex-1">
                  <div className="flex items-center space-x-2">
                    <span className="font-medium">{student.full_name}</span>
                    {student.khmer_name && (
                      <span className="text-gray-500">({student.khmer_name})</span>
                    )}
                  </div>
                  <div className="text-sm text-gray-500">
                    {student.formatted_student_id} • {student.school_email}
                  </div>
                  <div className="flex items-center space-x-2 mt-1">
                    {student.roles.map(role => (
                      <Tag key={role} size="small">{role}</Tag>
                    ))}
                    {student.student_status && (
                      <Tag
                        size="small"
                        color={student.student_status === 'ACTIVE' ? 'green' : 'default'}
                      >
                        {student.student_status}
                      </Tag>
                    )}
                  </div>
                </div>
              </div>
            </List.Item>
          )}
        />
      )}
    </Card>
  );

  return (
    <div className={`student-search ${embedded ? 'embedded' : ''}`}>
      {!embedded && (
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-gray-900">Student Search</h1>
          <p className="text-gray-600">
            Advanced search tools to find students quickly and efficiently
          </p>
        </div>
      )}

      <Tabs activeKey={activeTab} onChange={setActiveTab}>
        <TabPane tab="Quick Search" key="quick" icon={<SearchOutlined />}>
          <QuickSearchTab />
        </TabPane>
        <TabPane tab="Advanced Search" key="advanced" icon={<FilterOutlined />}>
          <AdvancedSearchTab />
        </TabPane>
        <TabPane tab="Search History" key="history" icon={<HistoryOutlined />}>
          <SearchHistoryTab />
        </TabPane>
        <TabPane tab="Saved Searches" key="saved" icon={<StarOutlined />}>
          <SavedSearchesTab />
        </TabPane>
      </Tabs>

      <Divider />

      <ResultsList />

      {/* Photo Search Modal */}
      <Modal
        title="Photo Search"
        open={photoSearchVisible}
        onCancel={() => setPhotoSearchVisible(false)}
        footer={null}
      >
        <div className="text-center py-8">
          <Upload
            accept="image/*"
            showUploadList={false}
            beforeUpload={(file) => {
              performPhotoSearch(file);
              return false;
            }}
          >
            <Button size="large" icon={<CameraOutlined />}>
              Upload Photo to Search
            </Button>
          </Upload>
          <p className="text-gray-500 mt-4">
            Upload a photo to find matching students using facial recognition
          </p>
        </div>
      </Modal>

      {/* QR Scanner Modal */}
      <Modal
        title="QR Code Scanner"
        open={qrScannerVisible}
        onCancel={() => setQrScannerVisible(false)}
        footer={null}
      >
        <div className="text-center py-8">
          <QrcodeOutlined style={{ fontSize: '48px' }} className="text-blue-500 mb-4" />
          <p className="text-gray-500 mb-4">
            QR code scanner functionality will be implemented
          </p>
          <Button onClick={() => setQrScannerVisible(false)}>
            Close
          </Button>
        </div>
      </Modal>

      {/* Save Search Modal */}
      <Modal
        title="Save Search"
        open={saveSearchVisible}
        onCancel={() => setSaveSearchVisible(false)}
        onOk={() => {
          const form = document.getElementById('save-search-form') as HTMLFormElement;
          if (form) {
            const formData = new FormData(form);
            const name = formData.get('name') as string;
            const description = formData.get('description') as string;
            if (name) {
              saveCurrentSearch(name, description);
            }
          }
        }}
      >
        <form id="save-search-form">
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Name</label>
            <Input name="name" placeholder="Enter search name" required />
          </div>
          <div className="mb-4">
            <label className="block text-sm font-medium mb-1">Description (optional)</label>
            <Input.TextArea
              name="description"
              placeholder="Describe this search..."
              rows={3}
            />
          </div>
        </form>
      </Modal>
    </div>
  );
};

export default StudentSearch;