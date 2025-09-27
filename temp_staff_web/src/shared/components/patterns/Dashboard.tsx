/**
 * Dashboard Pattern
 *
 * A comprehensive dashboard component for analytics and metrics:
 * - Grid layout with responsive cards
 * - Interactive charts and graphs
 * - Key metrics display
 * - Real-time data updates
 * - Customizable widgets
 * - Export capabilities
 * - Filter controls
 */

import React, { useState, useEffect } from 'react';
import {
  Card,
  Row,
  Col,
  Statistic,
  Select,
  DatePicker,
  Button,
  Space,
  Spin,
  Alert,
  Tooltip,
  Progress,
  Badge,
  Avatar,
  List,
  Tag,
  Empty,
} from 'antd';
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  UserOutlined,
  TeamOutlined,
  BookOutlined,
  DollarOutlined,
  CalendarOutlined,
  WarningOutlined,
  TrophyOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  ReloadOutlined,
  FilterOutlined,
  InfoCircleOutlined,
} from '@ant-design/icons';

const { Option } = Select;
const { RangePicker } = DatePicker;

export interface MetricCard {
  key: string;
  title: string;
  value: number | string;
  prefix?: React.ReactNode;
  suffix?: React.ReactNode;
  precision?: number;
  valueStyle?: React.CSSProperties;
  loading?: boolean;
  trend?: {
    value: number;
    isPositive: boolean;
    period: string;
  };
  target?: {
    value: number;
    label: string;
  };
  color?: string;
  icon?: React.ReactNode;
  onClick?: () => void;
}

export interface ChartWidget {
  key: string;
  title: string;
  type: 'line' | 'bar' | 'pie' | 'area' | 'column';
  data: any[];
  loading?: boolean;
  height?: number;
  config?: any;
  actions?: Array<{
    key: string;
    label: string;
    icon?: React.ReactNode;
    onClick: () => void;
  }>;
}

export interface ListWidget {
  key: string;
  title: string;
  data: Array<{
    id: string;
    title: string;
    description?: string;
    avatar?: string;
    status?: string;
    value?: number | string;
    trend?: 'up' | 'down' | 'stable';
    onClick?: () => void;
  }>;
  loading?: boolean;
  showMore?: () => void;
}

export interface Filter {
  key: string;
  label: string;
  type: 'select' | 'dateRange' | 'multiSelect';
  options?: Array<{ label: string; value: any }>;
  value?: any;
  onChange: (value: any) => void;
}

export interface DashboardProps {
  // Layout
  title?: string;
  description?: string;

  // Data
  metrics: MetricCard[];
  charts?: ChartWidget[];
  lists?: ListWidget[];
  loading?: boolean;

  // Filters
  filters?: Filter[];
  onFiltersChange?: (filters: Record<string, any>) => void;

  // Actions
  onRefresh?: () => void;
  onExport?: () => void;
  refreshInterval?: number; // milliseconds

  // Customization
  layout?: {
    metricsSpan?: number;
    chartSpan?: number;
    listSpan?: number;
  };
  showFilters?: boolean;
  showActions?: boolean;
}

export const Dashboard: React.FC<DashboardProps> = ({
  title,
  description,
  metrics,
  charts = [],
  lists = [],
  loading = false,
  filters = [],
  onFiltersChange,
  onRefresh,
  onExport,
  refreshInterval,
  layout = {
    metricsSpan: 6,
    chartSpan: 12,
    listSpan: 8,
  },
  showFilters = true,
  showActions = true,
}) => {
  const [filterValues, setFilterValues] = useState<Record<string, any>>({});
  const [autoRefreshTimer, setAutoRefreshTimer] = useState<NodeJS.Timeout | null>(null);

  // Auto-refresh functionality
  useEffect(() => {
    if (refreshInterval && onRefresh) {
      const timer = setInterval(() => {
        onRefresh();
      }, refreshInterval);

      setAutoRefreshTimer(timer);

      return () => {
        if (timer) {
          clearInterval(timer);
        }
      };
    }
  }, [refreshInterval, onRefresh]);

  // Cleanup auto-refresh timer
  useEffect(() => {
    return () => {
      if (autoRefreshTimer) {
        clearInterval(autoRefreshTimer);
      }
    };
  }, [autoRefreshTimer]);

  const handleFilterChange = (filterKey: string, value: any) => {
    const newFilters = { ...filterValues, [filterKey]: value };
    setFilterValues(newFilters);
    onFiltersChange?.(newFilters);
  };

  const renderMetricCard = (metric: MetricCard) => (
    <Card
      key={metric.key}
      hoverable={!!metric.onClick}
      onClick={metric.onClick}
      className="metric-card"
    >
      <div className="flex items-center justify-between">
        <div className="flex-1">
          <Statistic
            title={metric.title}
            value={metric.value}
            precision={metric.precision}
            valueStyle={metric.valueStyle}
            prefix={metric.prefix}
            suffix={metric.suffix}
            loading={metric.loading}
          />

          {metric.trend && (
            <div className="mt-2 flex items-center space-x-1">
              {metric.trend.isPositive ? (
                <ArrowUpOutlined className="text-green-500" />
              ) : (
                <ArrowDownOutlined className="text-red-500" />
              )}
              <span
                className={`text-sm ${
                  metric.trend.isPositive ? 'text-green-500' : 'text-red-500'
                }`}
              >
                {Math.abs(metric.trend.value)}% from {metric.trend.period}
              </span>
            </div>
          )}

          {metric.target && (
            <div className="mt-2">
              <div className="flex justify-between text-xs text-gray-500 mb-1">
                <span>{metric.target.label}</span>
                <span>{metric.target.value}</span>
              </div>
              <Progress
                percent={((Number(metric.value) / metric.target.value) * 100)}
                showInfo={false}
                size="small"
                strokeColor={metric.color}
              />
            </div>
          )}
        </div>

        {metric.icon && (
          <div className="text-2xl text-gray-400 ml-4">
            {metric.icon}
          </div>
        )}
      </div>
    </Card>
  );

  const renderChart = (chart: ChartWidget) => (
    <Card
      key={chart.key}
      title={chart.title}
      loading={chart.loading}
      extra={
        chart.actions && (
          <Space>
            {chart.actions.map(action => (
              <Button
                key={action.key}
                type="link"
                size="small"
                icon={action.icon}
                onClick={action.onClick}
              >
                {action.label}
              </Button>
            ))}
          </Space>
        )
      }
    >
      <div style={{ height: chart.height || 300 }}>
        {/* Chart component would go here - using placeholder for now */}
        <div className="flex items-center justify-center h-full bg-gray-50 rounded">
          <span className="text-gray-500">{chart.type.toUpperCase()} Chart</span>
        </div>
      </div>
    </Card>
  );

  const renderList = (listWidget: ListWidget) => (
    <Card
      key={listWidget.key}
      title={listWidget.title}
      loading={listWidget.loading}
      extra={
        listWidget.showMore && (
          <Button type="link" onClick={listWidget.showMore}>
            View All
          </Button>
        )
      }
    >
      <List
        dataSource={listWidget.data}
        locale={{
          emptyText: <Empty description="No data available" image={Empty.PRESENTED_IMAGE_SIMPLE} />
        }}
        renderItem={(item) => (
          <List.Item
            className={`${item.onClick ? 'cursor-pointer hover:bg-gray-50' : ''}`}
            onClick={item.onClick}
          >
            <div className="flex items-center justify-between w-full">
              <div className="flex items-center space-x-3">
                {item.avatar && (
                  <Avatar src={item.avatar} icon={<UserOutlined />} />
                )}
                <div>
                  <div className="font-medium">{item.title}</div>
                  {item.description && (
                    <div className="text-sm text-gray-500">{item.description}</div>
                  )}
                </div>
              </div>

              <div className="flex items-center space-x-2">
                {item.status && (
                  <Tag color={
                    item.status === 'active' ? 'green' :
                    item.status === 'inactive' ? 'red' :
                    item.status === 'pending' ? 'orange' :
                    'default'
                  }>
                    {item.status}
                  </Tag>
                )}

                {item.value && (
                  <div className="text-right">
                    <div className="font-medium">{item.value}</div>
                    {item.trend && (
                      <div className="text-xs">
                        {item.trend === 'up' && <ArrowUpOutlined className="text-green-500" />}
                        {item.trend === 'down' && <ArrowDownOutlined className="text-red-500" />}
                        {item.trend === 'stable' && <span className="text-gray-500">—</span>}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          </List.Item>
        )}
      />
    </Card>
  );

  return (
    <div className="dashboard">
      <Spin spinning={loading}>
        {/* Header */}
        {(title || description || showFilters || showActions) && (
          <div className="mb-6">
            <div className="flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4">
              {(title || description) && (
                <div>
                  {title && <h1 className="text-2xl font-bold text-gray-900">{title}</h1>}
                  {description && <p className="text-gray-600 mt-1">{description}</p>}
                </div>
              )}

              {(showFilters || showActions) && (
                <div className="flex flex-col sm:flex-row gap-3">
                  {/* Filters */}
                  {showFilters && filters.length > 0 && (
                    <Space wrap>
                      {filters.map(filter => (
                        <div key={filter.key}>
                          {filter.type === 'select' && (
                            <Select
                              placeholder={filter.label}
                              style={{ minWidth: 120 }}
                              value={filterValues[filter.key]}
                              onChange={(value) => handleFilterChange(filter.key, value)}
                              allowClear
                            >
                              {filter.options?.map(option => (
                                <Option key={option.value} value={option.value}>
                                  {option.label}
                                </Option>
                              ))}
                            </Select>
                          )}

                          {filter.type === 'dateRange' && (
                            <RangePicker
                              placeholder={['Start Date', 'End Date']}
                              value={filterValues[filter.key]}
                              onChange={(value) => handleFilterChange(filter.key, value)}
                            />
                          )}

                          {filter.type === 'multiSelect' && (
                            <Select
                              mode="multiple"
                              placeholder={filter.label}
                              style={{ minWidth: 150 }}
                              value={filterValues[filter.key]}
                              onChange={(value) => handleFilterChange(filter.key, value)}
                              allowClear
                            >
                              {filter.options?.map(option => (
                                <Option key={option.value} value={option.value}>
                                  {option.label}
                                </Option>
                              ))}
                            </Select>
                          )}
                        </div>
                      ))}
                    </Space>
                  )}

                  {/* Actions */}
                  {showActions && (
                    <Space>
                      {onRefresh && (
                        <Tooltip title={refreshInterval ? `Auto-refresh every ${refreshInterval / 1000}s` : 'Refresh data'}>
                          <Button
                            icon={<ReloadOutlined />}
                            onClick={onRefresh}
                          >
                            Refresh
                          </Button>
                        </Tooltip>
                      )}

                      {onExport && (
                        <Button
                          icon={<DownloadOutlined />}
                          onClick={onExport}
                        >
                          Export
                        </Button>
                      )}
                    </Space>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Metrics Cards */}
        <Row gutter={[16, 16]} className="mb-6">
          {metrics.map(metric => (
            <Col key={metric.key} xs={24} sm={12} lg={layout.metricsSpan}>
              {renderMetricCard(metric)}
            </Col>
          ))}
        </Row>

        {/* Charts and Lists */}
        <Row gutter={[16, 16]}>
          {charts.map(chart => (
            <Col key={chart.key} xs={24} lg={layout.chartSpan}>
              {renderChart(chart)}
            </Col>
          ))}

          {lists.map(list => (
            <Col key={list.key} xs={24} lg={layout.listSpan}>
              {renderList(list)}
            </Col>
          ))}
        </Row>
      </Spin>
    </div>
  );
};

export default Dashboard;