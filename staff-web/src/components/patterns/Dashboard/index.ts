/**
 * Analytics Dashboard Pattern - Core Exports
 * This is a simplified implementation focusing on the essential dashboard functionality
 */

export interface DashboardMetric {
  id: string;
  title: string;
  value: number | string;
  change?: number;
  changeType?: 'increase' | 'decrease' | 'neutral';
  icon?: React.ReactNode;
  color?: string;
}

export interface DashboardWidget {
  id: string;
  type: 'metric' | 'chart' | 'list';
  title: string;
  data: any;
  size: 'small' | 'medium' | 'large';
}

export interface DashboardProps {
  widgets: DashboardWidget[];
  metrics: DashboardMetric[];
  className?: string;
}

// Simplified Dashboard component
import React from 'react';

export const Dashboard: React.FC<DashboardProps> = ({ widgets, metrics, className = '' }) => {
  return (
    <div className={`dashboard-container ${className}`}>
      {/* Metrics Section */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        {metrics.map(metric => (
          <div key={metric.id} className="bg-white p-6 rounded-lg shadow">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-sm text-gray-600">{metric.title}</p>
                <p className="text-2xl font-bold text-gray-900">{metric.value}</p>
                {metric.change && (
                  <p className={`text-sm ${
                    metric.changeType === 'increase' ? 'text-green-600' :
                    metric.changeType === 'decrease' ? 'text-red-600' : 'text-gray-600'
                  }`}>
                    {metric.change > 0 ? '+' : ''}{metric.change}%
                  </p>
                )}
              </div>
              {metric.icon && (
                <div className={`p-3 rounded-full ${metric.color || 'bg-blue-100'}`}>
                  {metric.icon}
                </div>
              )}
            </div>
          </div>
        ))}
      </div>

      {/* Widgets Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 xl:grid-cols-3 gap-6">
        {widgets.map(widget => (
          <div
            key={widget.id}
            className={`bg-white p-6 rounded-lg shadow ${
              widget.size === 'large' ? 'lg:col-span-2' :
              widget.size === 'small' ? 'lg:col-span-1' : 'lg:col-span-1'
            }`}
          >
            <h3 className="text-lg font-medium text-gray-900 mb-4">{widget.title}</h3>
            <div className="dashboard-widget-content">
              {/* Widget content would be rendered here based on type */}
              <div className="text-gray-500">Widget content ({widget.type})</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};

export default Dashboard;