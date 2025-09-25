/**
 * Admin Panel Demo - Shows advanced admin functionality
 */

import React, { useState } from 'react';

const styles = {
  app: {
    minHeight: '100vh',
    backgroundColor: '#f9fafb',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  header: {
    backgroundColor: '#ffffff',
    borderBottom: '1px solid #e5e7eb',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    padding: '1rem 1.5rem',
  },
  headerContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
  },
  logo: {
    width: '40px',
    height: '40px',
    backgroundColor: '#dc2626',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
  },
  title: {
    fontSize: '1.25rem',
    fontWeight: 'bold',
    color: '#111827',
    margin: 0,
  },
  subtitle: {
    fontSize: '0.875rem',
    color: '#6b7280',
    margin: 0,
  },
  adminBadge: {
    backgroundColor: '#dc2626',
    color: 'white',
    padding: '0.25rem 0.5rem',
    borderRadius: '4px',
    fontSize: '0.75rem',
    fontWeight: '500',
    marginLeft: '0.5rem',
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '1rem',
  },
  modeToggle: {
    display: 'flex',
    backgroundColor: '#f3f4f6',
    borderRadius: '6px',
    padding: '2px',
  },
  modeBtn: {
    padding: '0.5rem 1rem',
    border: 'none',
    borderRadius: '4px',
    fontSize: '0.875rem',
    cursor: 'pointer',
    fontWeight: '500',
  },
  modeActive: {
    backgroundColor: '#dc2626',
    color: 'white',
  },
  modeInactive: {
    backgroundColor: 'transparent',
    color: '#374151',
  },
  signOutBtn: {
    backgroundColor: '#6b7280',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: '500',
  },
  layout: {
    display: 'flex',
    height: 'calc(100vh - 73px)',
  },
  sidebar: {
    width: '256px',
    backgroundColor: '#ffffff',
    borderRight: '1px solid #e5e7eb',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
  },
  sidebarNav: {
    marginTop: '1.5rem',
    padding: '0 1rem',
  },
  navSection: {
    marginBottom: '1.5rem',
  },
  navSectionTitle: {
    fontSize: '0.75rem',
    fontWeight: '600',
    color: '#9ca3af',
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
    margin: '0 0 0.5rem 0.75rem',
  },
  navList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '0.25rem',
  },
  navItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem',
    borderRadius: '8px',
    textDecoration: 'none',
    fontSize: '0.875rem',
    fontWeight: '500',
    cursor: 'pointer',
  },
  navItemActive: {
    backgroundColor: '#dc2626',
    color: '#ffffff',
  },
  navItemInactive: {
    color: '#374151',
    ':hover': {
      backgroundColor: '#f3f4f6',
    },
  },
  main: {
    flex: 1,
    overflowY: 'auto' as const,
    padding: '2rem',
  },
  pageTitle: {
    marginBottom: '2rem',
  },
  pageTitleH2: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    color: '#111827',
    margin: 0,
    marginBottom: '0.25rem',
  },
  pageTitleP: {
    color: '#6b7280',
    margin: 0,
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))',
    gap: '1.5rem',
    marginBottom: '2rem',
  },
  adminCard: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    border: '1px solid #e5e7eb',
    padding: '1.5rem',
    cursor: 'pointer',
    transition: 'all 0.2s',
  },
  adminCardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'between',
    marginBottom: '1rem',
  },
  adminIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: '1rem',
  },
  adminTitle: {
    fontSize: '1.125rem',
    fontWeight: '600',
    color: '#111827',
    margin: '0 0 0.5rem 0',
  },
  adminDesc: {
    fontSize: '0.875rem',
    color: '#6b7280',
    margin: 0,
    lineHeight: '1.4',
  },
  quickActions: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
    gap: '1rem',
    marginBottom: '2rem',
  },
  actionBtn: {
    backgroundColor: '#ffffff',
    border: '1px solid #d1d5db',
    borderRadius: '8px',
    padding: '1rem',
    textAlign: 'left' as const,
    cursor: 'pointer',
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#374151',
  },
  recentActivity: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    border: '1px solid #e5e7eb',
  },
  activityHeader: {
    padding: '1.5rem',
    borderBottom: '1px solid #e5e7eb',
  },
  activityContent: {
    padding: '1.5rem',
  },
  activityItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '0.75rem',
    padding: '0.75rem',
    borderRadius: '6px',
    marginBottom: '0.5rem',
  },
  activityIcon: {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    flexShrink: 0,
  },
  activityText: {
    fontSize: '0.875rem',
    color: '#374151',
    margin: 0,
  },
  activityTime: {
    fontSize: '0.75rem',
    color: '#9ca3af',
    marginLeft: 'auto',
  },
};

function App() {
  const [viewMode, setViewMode] = useState<'dashboard' | 'admin'>('admin');

  const switchToRegularDashboard = () => {
    // In real app, this would route to regular dashboard
    alert('Switching to regular staff dashboard view...');
  };

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.headerLeft}>
            <div style={styles.logo}>
              <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.07-1.78l-.717.717a1 1 0 000 1.414l.717.717a1 1 0 001.414 0l.717-.717a1 1 0 000-1.414l-.717-.717a1 1 0 00-1.414 0z" />
              </svg>
            </div>
            <div>
              <div style={{display: 'flex', alignItems: 'center'}}>
                <h1 style={styles.title}>NAGA SIS</h1>
                <span style={styles.adminBadge}>ADMIN</span>
              </div>
              <p style={styles.subtitle}>Administrative Control Panel</p>
            </div>
          </div>
          <div style={styles.headerRight}>
            <div style={styles.modeToggle}>
              <button
                style={{...styles.modeBtn, ...(viewMode === 'dashboard' ? styles.modeActive : styles.modeInactive)}}
                onClick={() => setViewMode('dashboard')}
              >
                Dashboard
              </button>
              <button
                style={{...styles.modeBtn, ...(viewMode === 'admin' ? styles.modeActive : styles.modeInactive)}}
                onClick={() => setViewMode('admin')}
              >
                Admin
              </button>
            </div>
            <button style={styles.signOutBtn}>Sign Out</button>
          </div>
        </div>
      </header>

      <div style={styles.layout}>
        {/* Admin Sidebar */}
        <aside style={styles.sidebar}>
          <nav style={styles.sidebarNav}>
            <div style={styles.navSection}>
              <h3 style={styles.navSectionTitle}>Overview</h3>
              <div style={styles.navList}>
                <div style={{...styles.navItem, ...styles.navItemActive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span>Admin Dashboard</span>
                </div>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                  <span>Analytics</span>
                </div>
              </div>
            </div>

            <div style={styles.navSection}>
              <h3 style={styles.navSectionTitle}>User Management</h3>
              <div style={styles.navList}>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                  </svg>
                  <span>Staff Accounts</span>
                </div>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.07-1.78l-.717.717a1 1 0 000 1.414l.717.717a1 1 0 001.414 0l.717-.717a1 1 0 000-1.414l-.717-.717a1 1 0 00-1.414 0z" />
                  </svg>
                  <span>Permissions</span>
                </div>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z" />
                  </svg>
                  <span>User Groups</span>
                </div>
              </div>
            </div>

            <div style={styles.navSection}>
              <h3 style={styles.navSectionTitle}>System</h3>
              <div style={styles.navList}>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                  </svg>
                  <span>System Settings</span>
                </div>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                  </svg>
                  <span>Database</span>
                </div>
                <div style={{...styles.navItem, ...styles.navItemInactive}}>
                  <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                  <span>Reports</span>
                </div>
              </div>
            </div>
          </nav>
        </aside>

        {/* Main Admin Content */}
        <main style={styles.main}>
          <div style={styles.pageTitle}>
            <h2 style={styles.pageTitleH2}>Administrative Dashboard</h2>
            <p style={styles.pageTitleP}>Manage users, system settings, and monitor activity</p>
          </div>

          {/* Quick Actions */}
          <div style={styles.quickActions}>
            <button style={styles.actionBtn}>
              <svg width="20" height="20" fill="none" stroke="#059669" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
              </svg>
              Add New Staff Member
            </button>
            <button style={styles.actionBtn}>
              <svg width="20" height="20" fill="none" stroke="#dc2626" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.07-1.78l-.717.717a1 1 0 000 1.414l.717.717a1 1 0 001.414 0l.717-.717a1 1 0 000-1.414l-.717-.717a1 1 0 00-1.414 0z" />
              </svg>
              Manage Permissions
            </button>
            <button style={styles.actionBtn}>
              <svg width="20" height="20" fill="none" stroke="#7c3aed" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
              </svg>
              Database Backup
            </button>
            <button style={styles.actionBtn} onClick={switchToRegularDashboard}>
              <svg width="20" height="20" fill="none" stroke="#1d4ed8" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
              View Regular Dashboard
            </button>
          </div>

          {/* Admin Control Panels */}
          <div style={styles.grid}>
            <div style={styles.adminCard}>
              <div style={{...styles.adminIcon, backgroundColor: '#dbeafe'}}>
                <svg width="24" height="24" fill="none" stroke="#1d4ed8" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
              </div>
              <h3 style={styles.adminTitle}>User Management</h3>
              <p style={styles.adminDesc}>
                Manage staff accounts, roles, and permissions. Create new users, reset passwords, and control access levels.
                <br/><strong>23 active staff accounts</strong>
              </p>
            </div>

            <div style={styles.adminCard}>
              <div style={{...styles.adminIcon, backgroundColor: '#d1fae5'}}>
                <svg width="24" height="24" fill="none" stroke="#059669" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <h3 style={styles.adminTitle}>System Configuration</h3>
              <p style={styles.adminDesc}>
                Configure academic terms, grading scales, notification settings, and system-wide preferences.
                <br/><strong>Last updated: 2 days ago</strong>
              </p>
            </div>

            <div style={styles.adminCard}>
              <div style={{...styles.adminIcon, backgroundColor: '#fef3c7'}}>
                <svg width="24" height="24" fill="none" stroke="#d97706" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4" />
                </svg>
              </div>
              <h3 style={styles.adminTitle}>Data Management</h3>
              <p style={styles.adminDesc}>
                Database backups, data import/export, system maintenance, and performance monitoring.
                <br/><strong>Last backup: Today 6:00 AM</strong>
              </p>
            </div>

            <div style={styles.adminCard}>
              <div style={{...styles.adminIcon, backgroundColor: '#ede9fe'}}>
                <svg width="24" height="24" fill="none" stroke="#7c3aed" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
              </div>
              <h3 style={styles.adminTitle}>Advanced Reports</h3>
              <p style={styles.adminDesc}>
                Generate comprehensive reports, audit logs, usage analytics, and compliance documentation.
                <br/><strong>15 scheduled reports</strong>
              </p>
            </div>
          </div>

          {/* Recent Admin Activity */}
          <div style={styles.recentActivity}>
            <div style={styles.activityHeader}>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0}}>Recent Administrative Activity</h3>
              <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Latest system changes and user actions</p>
            </div>
            <div style={styles.activityContent}>
              <div style={{...styles.activityItem, backgroundColor: '#f0fdf4'}}>
                <div style={{...styles.activityIcon, backgroundColor: '#22c55e'}}></div>
                <p style={styles.activityText}>New staff member "Sarah Johnson" added with Teacher permissions</p>
                <span style={styles.activityTime}>2 hours ago</span>
              </div>

              <div style={{...styles.activityItem, backgroundColor: '#eff6ff'}}>
                <div style={{...styles.activityIcon, backgroundColor: '#3b82f6'}}></div>
                <p style={styles.activityText}>System backup completed successfully (1.2 GB)</p>
                <span style={styles.activityTime}>6 hours ago</span>
              </div>

              <div style={{...styles.activityItem, backgroundColor: '#fef3c7'}}>
                <div style={{...styles.activityIcon, backgroundColor: '#f59e0b'}}></div>
                <p style={styles.activityText}>Permission updated for "Mike Chen" - added Grade Access</p>
                <span style={styles.activityTime}>1 day ago</span>
              </div>

              <div style={{...styles.activityItem, backgroundColor: '#fef2f2'}}>
                <div style={{...styles.activityIcon, backgroundColor: '#ef4444'}}></div>
                <p style={styles.activityText}>Failed login attempt from unknown IP address</p>
                <span style={styles.activityTime}>2 days ago</span>
              </div>

              <div style={{...styles.activityItem, backgroundColor: '#f5f3ff'}}>
                <div style={{...styles.activityIcon, backgroundColor: '#8b5cf6'}}></div>
                <p style={styles.activityText}>Academic calendar updated for Spring 2025 term</p>
                <span style={styles.activityTime}>3 days ago</span>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

export default App;