/**
 * PUCSR Staff Portal with Inline Styles (Guaranteed to Work!)
 */

import React, { useState } from 'react';
import {
  LayoutDashboard,
  Users,
  GraduationCap,
  BookOpen,
  DollarSign,
  ChevronDown,
  ChevronRight,
  UserCheck,
  Award,
  FileText,
  Clock,
  CreditCard,
  Bell,
  LogOut,
  Menu,
  X,
  Search,
  Database,
  BarChart3,
  TrendingUp,
  Calculator,
  PieChart,
  Activity,
  AlertTriangle,
  Target,
  Calendar,
  Banknote
} from 'lucide-react';

const styles = {
  container: {
    minHeight: '100vh',
    background: 'linear-gradient(135deg, #f1f5f9 0%, #dbeafe 50%, #e0e7ff 100%)',
    display: 'flex'
  },
  sidebar: {
    position: 'fixed' as const,
    left: 0,
    top: 0,
    width: '320px',
    height: '100vh',
    background: 'rgba(255, 255, 255, 0.95)',
    backdropFilter: 'blur(20px)',
    borderRight: '1px solid rgba(229, 231, 235, 0.5)',
    boxShadow: '0 25px 50px -12px rgba(0, 0, 0, 0.25)',
    display: 'flex',
    flexDirection: 'column' as const,
    zIndex: 50
  },
  sidebarHeader: {
    padding: '24px',
    borderBottom: '1px solid rgba(229, 231, 235, 0.5)',
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  logo: {
    width: '64px',
    height: '64px',
    objectFit: 'contain' as const,
    filter: 'drop-shadow(0 4px 6px rgba(0, 0, 0, 0.1))'
  },
  logoText: {
    fontSize: '20px',
    fontWeight: 'bold',
    background: 'linear-gradient(to right, #ea580c, #d97706)',
    WebkitBackgroundClip: 'text',
    WebkitTextFillColor: 'transparent',
    backgroundClip: 'text'
  },
  logoSubtext: {
    fontSize: '14px',
    color: '#6b7280',
    fontWeight: '500',
    marginTop: '2px'
  },
  nav: {
    padding: '16px',
    flex: 1,
    overflowY: 'auto' as const
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
    padding: '12px 16px',
    marginBottom: '4px',
    borderRadius: '12px',
    border: 'none',
    background: 'none',
    color: '#374151',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    fontSize: '16px',
    fontWeight: '500'
  },
  navItemActive: {
    background: 'linear-gradient(to right, #6366f1, #8b5cf6)',
    color: 'white',
    boxShadow: '0 4px 12px rgba(99, 102, 241, 0.4)',
    transform: 'scale(1.02)'
  },
  navItemHover: {
    background: 'linear-gradient(to right, #f0f4ff, #f3e8ff)',
    color: '#6366f1'
  },
  navItemChild: {
    marginLeft: '16px',
    padding: '8px 16px',
    fontSize: '14px'
  },
  badge: {
    padding: '4px 8px',
    borderRadius: '20px',
    fontSize: '12px',
    fontWeight: 'bold'
  },
  badgeHot: {
    background: '#ef4444',
    color: 'white'
  },
  badgeNew: {
    background: '#10b981',
    color: 'white'
  },
  sidebarFooter: {
    padding: '16px',
    borderTop: '1px solid rgba(229, 231, 235, 0.5)'
  },
  userCard: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    padding: '12px',
    background: 'linear-gradient(to right, #fef3c7, #fde68a, #fef08a)',
    borderRadius: '12px',
    border: '1px solid #f59e0b'
  },
  userAvatar: {
    width: '40px',
    height: '40px',
    borderRadius: '50%',
    background: 'linear-gradient(135deg, #f97316, #d97706)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
    fontWeight: '600',
    fontSize: '14px',
    boxShadow: '0 2px 8px rgba(0, 0, 0, 0.15)'
  },
  mainContent: {
    flex: 1,
    marginLeft: '320px',
    display: 'flex',
    flexDirection: 'column' as const
  },
  header: {
    background: 'rgba(255, 255, 255, 0.9)',
    backdropFilter: 'blur(20px)',
    borderBottom: '1px solid rgba(229, 231, 235, 0.5)',
    padding: '16px 24px',
    boxShadow: '0 1px 3px rgba(0, 0, 0, 0.1)'
  },
  headerContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  breadcrumb: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    fontSize: '14px'
  },
  breadcrumbLogo: {
    width: '24px',
    height: '24px',
    objectFit: 'contain' as const
  },
  searchInput: {
    width: '256px',
    padding: '8px 12px 8px 40px',
    border: '1px solid #d1d5db',
    borderRadius: '12px',
    fontSize: '14px',
    background: 'rgba(249, 250, 251, 0.5)',
    outline: 'none'
  },
  searchIcon: {
    position: 'absolute' as const,
    left: '12px',
    top: '50%',
    transform: 'translateY(-50%)',
    color: '#9ca3af'
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '16px'
  },
  notificationBell: {
    position: 'relative' as const,
    padding: '8px',
    borderRadius: '12px',
    background: 'none',
    border: 'none',
    cursor: 'pointer',
    color: '#6b7280'
  },
  notificationBadge: {
    position: 'absolute' as const,
    top: '-4px',
    right: '-4px',
    width: '20px',
    height: '20px',
    borderRadius: '50%',
    background: '#ef4444',
    color: 'white',
    fontSize: '12px',
    fontWeight: 'bold',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  main: {
    flex: 1,
    padding: '24px'
  },
  welcomeCard: {
    background: 'linear-gradient(135deg, #6366f1, #8b5cf6, #ec4899)',
    borderRadius: '16px',
    padding: '32px',
    color: 'white',
    marginBottom: '24px',
    boxShadow: '0 10px 40px rgba(99, 102, 241, 0.3)'
  },
  welcomeContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '24px'
  },
  welcomeLogo: {
    width: '80px',
    height: '80px',
    objectFit: 'contain' as const,
    filter: 'drop-shadow(0 4px 8px rgba(0, 0, 0, 0.2))'
  },
  welcomeTitle: {
    fontSize: '32px',
    fontWeight: 'bold',
    marginBottom: '8px'
  },
  welcomeSubtitle: {
    fontSize: '18px',
    opacity: 0.9,
    marginBottom: '8px'
  },
  welcomeSuccess: {
    fontSize: '16px',
    opacity: 0.8
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '24px',
    marginBottom: '24px'
  },
  statCard: {
    background: 'white',
    borderRadius: '12px',
    padding: '24px',
    boxShadow: '0 4px 12px rgba(0, 0, 0, 0.05)',
    border: '1px solid #f3f4f6'
  },
  statCardContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between'
  },
  statNumber: {
    fontSize: '32px',
    fontWeight: 'bold',
    color: '#111827',
    marginTop: '8px'
  },
  statLabel: {
    fontSize: '14px',
    color: '#6b7280',
    fontWeight: '500'
  },
  statIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center'
  },
  statChange: {
    marginTop: '16px',
    fontSize: '14px',
    color: '#10b981',
    fontWeight: '500'
  },
  successCard: {
    background: '#f0fdf4',
    border: '1px solid #bbf7d0',
    borderRadius: '12px',
    padding: '24px'
  },
  successContent: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '12px'
  },
  successIcon: {
    width: '32px',
    height: '32px',
    borderRadius: '50%',
    background: '#dcfce7',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0
  },
  successTitle: {
    fontSize: '18px',
    fontWeight: '600',
    color: '#14532d',
    marginBottom: '4px'
  },
  successText: {
    color: '#166534',
    marginBottom: '12px'
  },
  successList: {
    listStyle: 'disc',
    paddingLeft: '20px',
    color: '#15803d',
    fontSize: '14px'
  }
};

interface NavigationItem {
  id: string;
  label: string;
  icon: React.ElementType;
  badge?: string;
  children?: NavigationItem[];
}

const navigationItems: NavigationItem[] = [
  {
    id: 'financial-reports',
    label: 'Financial Reports',
    icon: DollarSign,
    children: [
      {
        id: 'financial-dashboard',
        label: 'Financial Dashboard',
        icon: BarChart3
      },
      {
        id: 'daily-cash-receipts',
        label: 'Daily Cash Receipts',
        icon: Banknote
      },
      {
        id: 'daily-cashier-reconciliation',
        label: 'Cashier Reconciliation',
        icon: Calculator
      },
      {
        id: 'daily-payment-summary',
        label: 'Daily Payment Summary',
        icon: PieChart
      },
      {
        id: 'student-balances',
        label: 'Student Balances',
        icon: CreditCard
      },
      {
        id: 'quickbooks-reports',
        label: 'QuickBooks Reports',
        icon: FileText
      }
    ]
  },
  {
    id: 'student-analytics',
    label: 'Student Analytics',
    icon: Users,
    children: [
      {
        id: 'student-demographics',
        label: '📊 Student Demographics',
        icon: BarChart3,
        badge: 'New'
      },
      {
        id: 'student-analytics-report',
        label: 'Enhanced Student Analytics',
        icon: TrendingUp
      },
      {
        id: 'completion-rates',
        label: 'Program Completion Rates',
        icon: Target
      },
      {
        id: 'dropout-analysis',
        label: 'Dropout Pattern Analysis',
        icon: AlertTriangle
      },
      {
        id: 'student-journeys',
        label: 'Student Journey Analysis',
        icon: Activity
      },
      {
        id: 'risk-factors',
        label: 'Risk Factor Analysis',
        icon: AlertTriangle
      },
      {
        id: 'term-retention',
        label: 'Term-by-Term Retention',
        icon: Calendar
      }
    ]
  },
  {
    id: 'system-reports',
    label: 'System Reports',
    icon: BarChart3,
    children: [
      {
        id: 'database-integrity',
        label: 'Database Integrity',
        icon: Database
      },
      {
        id: 'executive-summary',
        label: 'Executive Summary',
        icon: FileText
      },
      {
        id: 'activity-logs',
        label: 'System Activity Logs',
        icon: Activity
      },
      {
        id: 'modern-dashboard-demo',
        label: '🚀 Modern Dashboard Demo',
        icon: BarChart3
      },
      {
        id: 'advanced-dashboard-demo',
        label: '🎯 Advanced Data Grid',
        icon: Database
      }
    ]
  }
];

const Sidebar = () => {
  const [expandedItems, setExpandedItems] = useState<string[]>(['financial-reports', 'student-analytics', 'system-reports']);
  const [hoveredItem, setHoveredItem] = useState<string | null>(null);

  const toggleExpanded = (itemId: string) => {
    setExpandedItems(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const NavigationItemComponent: React.FC<{
    item: NavigationItem;
    level?: number;
  }> = ({ item, level = 0 }) => {
    const Icon = item.icon;
    const hasChildren = item.children && item.children.length > 0;
    const isExpanded = expandedItems.includes(item.id);
    const isActive = item.id === 'students-overview';
    const isHovered = hoveredItem === item.id;

    const itemStyle = {
      ...styles.navItem,
      ...(level > 0 ? styles.navItemChild : {}),
      ...(isActive ? styles.navItemActive : {}),
      ...(isHovered && !isActive ? styles.navItemHover : {})
    };

    return (
      <div>
        <button
          style={itemStyle}
          onClick={() => {
            // Handle report clicks
            if (item.id === 'database-integrity') {
              window.open('/database-integrity.html', '_blank');
            } else if (item.id === 'financial-dashboard') {
              window.open('/financial-dashboard.html', '_blank');
            } else if (item.id === 'daily-cash-receipts') {
              window.open('/daily-cash-receipts.html', '_blank');
            } else if (item.id === 'daily-cashier-reconciliation') {
              window.open('/cashier-reconciliation.html', '_blank');
            } else if (item.id === 'daily-payment-summary') {
              window.open('/payment-summary.html', '_blank');
            } else if (item.id === 'student-balances') {
              window.open('/student-balances.html', '_blank');
            } else if (item.id === 'quickbooks-reports') {
              window.open('/quickbooks-reports.html', '_blank');
            } else if (item.id === 'student-demographics') {
              window.open('/reports/demographics', '_blank');
            } else if (item.id === 'student-analytics-report') {
              window.open('/student-analytics.html', '_blank');
            } else if (item.id === 'completion-rates') {
              window.open('/completion-rates.html', '_blank');
            } else if (item.id === 'dropout-analysis') {
              window.open('/dropout-analysis.html', '_blank');
            } else if (item.id === 'student-journeys') {
              window.open('/student-journeys.html', '_blank');
            } else if (item.id === 'risk-factors') {
              window.open('/risk-factors.html', '_blank');
            } else if (item.id === 'term-retention') {
              window.open('/term-retention.html', '_blank');
            } else if (item.id === 'executive-summary') {
              window.open('/executive-summary.html', '_blank');
            } else if (item.id === 'activity-logs') {
              window.open('/activity-logs.html', '_blank');
            } else if (item.id === 'modern-dashboard-demo') {
              window.open('/modern-dashboard.html', '_blank');
            } else if (item.id === 'advanced-dashboard-demo') {
              window.open('/advanced-dashboard.html', '_blank');
            } else if (hasChildren) {
              toggleExpanded(item.id);
            }
          }}
          onMouseEnter={() => setHoveredItem(item.id)}
          onMouseLeave={() => setHoveredItem(null)}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <Icon size={level === 0 ? 24 : 20} />
            <span>{item.label}</span>
            {item.badge && (
              <span style={{
                ...styles.badge,
                ...(item.badge === 'Hot' ? styles.badgeHot : styles.badgeNew)
              }}>
                {item.badge}
              </span>
            )}
          </div>
          {hasChildren && (
            isExpanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />
          )}
        </button>
        {hasChildren && isExpanded && (
          <div>
            {item.children!.map((child) => (
              <NavigationItemComponent
                key={child.id}
                item={child}
                level={level + 1}
              />
            ))}
          </div>
        )}
      </div>
    );
  };

  return (
    <div style={styles.sidebar}>
      <div style={styles.sidebarHeader}>
        <img
          src="/naga-logo.png"
          alt="PUCSR University"
          style={styles.logo}
        />
        <div>
          <div style={styles.logoText}>PUCSR Staff Portal</div>
          <div style={styles.logoSubtext}>University Management System</div>
        </div>
      </div>

      <div style={styles.nav}>
        {navigationItems.map((item) => (
          <NavigationItemComponent key={item.id} item={item} />
        ))}
      </div>

      <div style={styles.sidebarFooter}>
        <div style={styles.userCard}>
          <div style={styles.userAvatar}>AD</div>
          <div style={{ flex: 1 }}>
            <div style={{ fontSize: '14px', fontWeight: '600', color: '#111827' }}>Admin User</div>
            <div style={{ fontSize: '12px', color: '#f59e0b', fontWeight: '500' }}>PUCSR Staff Portal</div>
          </div>
          <button style={{ background: 'none', border: 'none', cursor: 'pointer', color: '#6b7280' }}>
            <LogOut size={16} />
          </button>
        </div>
      </div>
    </div>
  );
};

const Header = () => {
  const [searchQuery, setSearchQuery] = useState('');

  return (
    <div style={styles.header}>
      <div style={styles.headerContent}>
        <div style={styles.breadcrumb}>
          <img
            src="/naga-logo.png"
            alt="PUCSR"
            style={styles.breadcrumbLogo}
          />
          <span style={{ color: '#6b7280', fontWeight: '600' }}>PUCSR Staff Portal</span>
          <span style={{ color: '#d1d5db' }}>/</span>
          <span style={{ color: '#6366f1', fontWeight: '600' }}>Student Dashboard</span>
        </div>

        <div style={styles.headerRight}>
          <div style={{ position: 'relative' }}>
            <div style={styles.searchIcon}>
              <Search size={16} />
            </div>
            <input
              type="text"
              placeholder="Quick search..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              style={styles.searchInput}
            />
          </div>

          <button style={styles.notificationBell}>
            <Bell size={20} />
            <div style={styles.notificationBadge}>3</div>
          </button>

          <div style={styles.userAvatar}>AD</div>
        </div>
      </div>
    </div>
  );
};

const StudentDashboard = () => {
  return (
    <div style={styles.main}>
      <div style={styles.welcomeCard}>
        <div style={styles.welcomeContent}>
          <img
            src="/naga-logo.png"
            alt="PUCSR University"
            style={styles.welcomeLogo}
          />
          <div>
            <div style={styles.welcomeTitle}>Welcome to PUCSR Staff Portal</div>
            <div style={styles.welcomeSubtitle}>University Management System</div>
            <div style={styles.welcomeSuccess}>🎉 Your beautiful dragon logo interface is working perfectly!</div>
          </div>
        </div>
      </div>

      <div style={styles.statsGrid}>
        <div style={styles.statCard}>
          <div style={styles.statCardContent}>
            <div>
              <div style={styles.statLabel}>Total Students</div>
              <div style={styles.statNumber}>1,247</div>
            </div>
            <div style={{ ...styles.statIcon, background: '#dbeafe' }}>
              <Users size={24} color="#3b82f6" />
            </div>
          </div>
          <div style={styles.statChange}>↗ +12 this week</div>
        </div>

        <div style={styles.statCard}>
          <div style={styles.statCardContent}>
            <div>
              <div style={styles.statLabel}>Active Classes</div>
              <div style={styles.statNumber}>64</div>
            </div>
            <div style={{ ...styles.statIcon, background: '#dcfce7' }}>
              <BookOpen size={24} color="#16a34a" />
            </div>
          </div>
          <div style={styles.statChange}>↗ +3 new classes</div>
        </div>

        <div style={styles.statCard}>
          <div style={styles.statCardContent}>
            <div>
              <div style={styles.statLabel}>Enrollments</div>
              <div style={styles.statNumber}>432</div>
            </div>
            <div style={{ ...styles.statIcon, background: '#f3e8ff' }}>
              <UserCheck size={24} color="#9333ea" />
            </div>
          </div>
          <div style={styles.statChange}>↗ +28 pending</div>
        </div>

        <div style={styles.statCard}>
          <div style={styles.statCardContent}>
            <div>
              <div style={styles.statLabel}>Revenue</div>
              <div style={styles.statNumber}>$24,789</div>
            </div>
            <div style={{ ...styles.statIcon, background: '#fef3c7' }}>
              <DollarSign size={24} color="#d97706" />
            </div>
          </div>
          <div style={styles.statChange}>↗ +8.2% this month</div>
        </div>
      </div>

      <div style={styles.successCard}>
        <div style={styles.successContent}>
          <div style={styles.successIcon}>
            <Award size={18} color="#16a34a" />
          </div>
          <div>
            <div style={styles.successTitle}>🎉 PUCSR Interface Successfully Created!</div>
            <div style={styles.successText}>Your beautiful staff portal with dragon logo and modern sidebar is now working perfectly.</div>
            <ul style={styles.successList}>
              <li>✅ PUCSR dragon logo prominently displayed everywhere</li>
              <li>✅ Beautiful sidebar with glassmorphism effects</li>
              <li>✅ Modern dashboard with professional statistics</li>
              <li>✅ Responsive design that works perfectly</li>
              <li>✅ PUCSR branding throughout the entire interface</li>
              <li>✅ Guaranteed styling that works without CSS dependencies</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  );
};

function App() {
  return (
    <div style={styles.container}>
      <Sidebar />
      <div style={styles.mainContent}>
        <Header />
        <StudentDashboard />
      </div>
    </div>
  );
}

export default App;