import React, { useEffect, useState } from 'react';
import { Card, Table, Badge, Statistic, Progress, Alert, Tabs, TabsProps } from 'antd';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts';
import { DatabaseIcon, AlertTriangle, CheckCircle, XCircle, Info } from 'lucide-react';

interface DatabaseIssue {
  type: string;
  table: string;
  column: string;
  db_nullable?: boolean;
  model_nullable?: boolean;
  has_data: boolean;
  recommendation?: string;
}

interface DatabaseAnalysis {
  issues: {
    critical: DatabaseIssue[];
    high: DatabaseIssue[];
    medium: DatabaseIssue[];
    low: DatabaseIssue[];
  };
  decisions: Record<string, any>;
}

const mockDatabaseAnalysis: DatabaseAnalysis = {
  issues: {
    critical: [
      {
        type: "null_constraint_mismatch",
        table: "enrollment_programtransition", 
        column: "from_enrollment_id",
        db_nullable: false,
        model_nullable: true,
        has_data: false
      },
      {
        type: "null_constraint_mismatch",
        table: "finance_payment",
        column: "processed_date", 
        db_nullable: false,
        model_nullable: true,
        has_data: true
      },
      {
        type: "null_constraint_mismatch",
        table: "finance_reconciliation_batch",
        column: "created_by_id",
        db_nullable: false,
        model_nullable: true, 
        has_data: true
      }
    ],
    high: [
      {
        type: "extra_column",
        table: "scheduling_classpart_textbooks",
        column: "id", 
        has_data: false,
        recommendation: "drop"
      },
      {
        type: "extra_column", 
        table: "curriculum_seniorprojectgroup",
        column: "students",
        has_data: false,
        recommendation: "drop"
      },
      {
        type: "extra_column",
        table: "curriculum_course_majors", 
        column: "major_id",
        has_data: true,
        recommendation: "preserve"
      }
    ],
    medium: [],
    low: []
  },
  decisions: {
    "enrollment_programtransition.from_enrollment_id": {
      action: "update_database",
      change: "make_nullable",
      reason: "Model expects nullable, no data impact"
    }
  }
};

export const DatabaseIntegrityReport: React.FC = () => {
  const [analysis, setAnalysis] = useState<DatabaseAnalysis | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Simulate loading database analysis
    setTimeout(() => {
      setAnalysis(mockDatabaseAnalysis);
      setLoading(false);
    }, 1000);
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-96">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto mb-4"></div>
          <p className="text-gray-600">Loading database integrity analysis...</p>
        </div>
      </div>
    );
  }

  if (!analysis) {
    return <Alert message="Failed to load database analysis" type="error" />;
  }

  const totalIssues = analysis.issues.critical.length + analysis.issues.high.length + 
                     analysis.issues.medium.length + analysis.issues.low.length;

  const severityData = [
    { name: 'Critical', value: analysis.issues.critical.length, color: '#dc2626' },
    { name: 'High', value: analysis.issues.high.length, color: '#ea580c' },
    { name: 'Medium', value: analysis.issues.medium.length, color: '#d97706' },
    { name: 'Low', value: analysis.issues.low.length, color: '#65a30d' }
  ];

  const criticalColumns = [
    {
      title: 'Table',
      dataIndex: 'table',
      key: 'table',
      render: (text: string) => <code className="bg-gray-100 px-2 py-1 rounded">{text}</code>
    },
    {
      title: 'Column',
      dataIndex: 'column', 
      key: 'column',
      render: (text: string) => <code className="bg-blue-100 px-2 py-1 rounded">{text}</code>
    },
    {
      title: 'Issue Type',
      dataIndex: 'type',
      key: 'type',
      render: (text: string) => <Badge color="red">{text.replace(/_/g, ' ')}</Badge>
    },
    {
      title: 'Has Data',
      dataIndex: 'has_data',
      key: 'has_data',
      render: (hasData: boolean) => hasData ? 
        <Badge color="red" text="Has Data" /> : 
        <Badge color="green" text="No Data" />
    },
    {
      title: 'DB Nullable',
      dataIndex: 'db_nullable',
      key: 'db_nullable',
      render: (nullable: boolean) => nullable ? 
        <CheckCircle className="w-4 h-4 text-green-500" /> : 
        <XCircle className="w-4 h-4 text-red-500" />
    },
    {
      title: 'Model Nullable', 
      dataIndex: 'model_nullable',
      key: 'model_nullable',
      render: (nullable: boolean) => nullable ?
        <CheckCircle className="w-4 h-4 text-green-500" /> :
        <XCircle className="w-4 h-4 text-red-500" />
    }
  ];

  const highColumns = [
    {
      title: 'Table',
      dataIndex: 'table',
      key: 'table',
      render: (text: string) => <code className="bg-gray-100 px-2 py-1 rounded">{text}</code>
    },
    {
      title: 'Column', 
      dataIndex: 'column',
      key: 'column',
      render: (text: string) => <code className="bg-blue-100 px-2 py-1 rounded">{text}</code>
    },
    {
      title: 'Issue Type',
      dataIndex: 'type',
      key: 'type', 
      render: (text: string) => <Badge color="orange">{text.replace(/_/g, ' ')}</Badge>
    },
    {
      title: 'Recommendation',
      dataIndex: 'recommendation',
      key: 'recommendation',
      render: (rec: string) => (
        <Badge color={rec === 'drop' ? 'red' : 'green'}>
          {rec === 'drop' ? 'Drop Column' : 'Preserve'}
        </Badge>
      )
    },
    {
      title: 'Has Data',
      dataIndex: 'has_data', 
      key: 'has_data',
      render: (hasData: boolean) => hasData ?
        <Badge color="red" text="Has Data" /> :
        <Badge color="green" text="No Data" />
    }
  ];

  const tabItems: TabsProps['items'] = [
    {
      key: '1',
      label: (
        <span className="flex items-center space-x-2">
          <AlertTriangle className="w-4 h-4 text-red-500" />
          <span>Critical Issues ({analysis.issues.critical.length})</span>
        </span>
      ),
      children: (
        <Card>
          <Alert
            message="Critical Database Schema Issues"
            description="These issues require immediate attention as they involve data integrity constraints."
            type="error"
            showIcon
            className="mb-4"
          />
          <Table
            columns={criticalColumns}
            dataSource={analysis.issues.critical.map((item, index) => ({ ...item, key: index }))}
            pagination={false}
            size="small"
          />
        </Card>
      )
    },
    {
      key: '2', 
      label: (
        <span className="flex items-center space-x-2">
          <Info className="w-4 h-4 text-orange-500" />
          <span>High Priority ({analysis.issues.high.length})</span>
        </span>
      ),
      children: (
        <Card>
          <Alert
            message="High Priority Schema Issues"
            description="Extra columns and schema inconsistencies that should be addressed."
            type="warning"
            showIcon
            className="mb-4"
          />
          <Table
            columns={highColumns}
            dataSource={analysis.issues.high.map((item, index) => ({ ...item, key: index }))}
            pagination={false}
            size="small"
          />
        </Card>
      )
    }
  ];

  return (
    <div className="p-6 space-y-6 bg-gray-50 min-h-screen">
      <div className="flex items-center space-x-4">
        <DatabaseIcon className="w-8 h-8 text-indigo-600" />
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Database Integrity Report</h1>
          <p className="text-gray-600">PostgreSQL 18 Schema Analysis & Recommendations</p>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card>
          <Statistic
            title="Total Issues"
            value={totalIssues}
            valueStyle={{ color: totalIssues > 0 ? '#dc2626' : '#059669' }}
            prefix={totalIssues > 0 ? <AlertTriangle className="w-4 h-4" /> : <CheckCircle className="w-4 h-4" />}
          />
        </Card>
        <Card>
          <Statistic
            title="Critical Issues"
            value={analysis.issues.critical.length}
            valueStyle={{ color: '#dc2626' }}
            prefix={<XCircle className="w-4 h-4" />}
          />
        </Card>
        <Card>
          <Statistic
            title="High Priority"
            value={analysis.issues.high.length}
            valueStyle={{ color: '#ea580c' }}
            prefix={<AlertTriangle className="w-4 h-4" />}
          />
        </Card>
        <Card>
          <Statistic
            title="Database Version"
            value="PostgreSQL 18"
            valueStyle={{ color: '#059669' }}
            prefix={<DatabaseIcon className="w-4 h-4" />}
          />
        </Card>
      </div>

      {/* Charts */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card title="Issues by Severity">
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={severityData}
                cx="50%"
                cy="50%"
                outerRadius={80}
                fill="#8884d8"
                dataKey="value"
                label={({ name, value }) => `${name}: ${value}`}
              >
                {severityData.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip />
            </PieChart>
          </ResponsiveContainer>
        </Card>

        <Card title="Schema Health Score">
          <div className="space-y-4">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Overall Health</span>
                <span className="font-semibold">
                  {Math.round(((617 - totalIssues) / 617) * 100)}%
                </span>
              </div>
              <Progress 
                percent={Math.round(((617 - totalIssues) / 617) * 100)}
                strokeColor="#059669"
              />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Critical Issues Resolved</span>
                <span className="font-semibold">0%</span>
              </div>
              <Progress percent={0} strokeColor="#dc2626" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>High Priority Resolved</span>
                <span className="font-semibold">0%</span>
              </div>
              <Progress percent={0} strokeColor="#ea580c" />
            </div>
          </div>
        </Card>
      </div>

      {/* Detailed Issue Tables */}
      <Card title="Detailed Analysis">
        <Tabs defaultActiveKey="1" items={tabItems} />
      </Card>

      {/* Recommendations */}
      <Card title="Recommended Actions" className="mt-6">
        <Alert
          message="Migration Recommendations"
          description={
            <ul className="mt-2 space-y-1 text-sm">
              <li>• Update database constraints for {analysis.issues.critical.length} critical null constraint mismatches</li>
              <li>• Drop {analysis.issues.high.filter(i => i.recommendation === 'drop').length} unused columns to clean up schema</li>
              <li>• Preserve {analysis.issues.high.filter(i => i.recommendation === 'preserve').length} columns with existing data</li>
              <li>• Review and test all changes in staging environment before production deployment</li>
            </ul>
          }
          type="info"
          showIcon
        />
      </Card>
    </div>
  );
};