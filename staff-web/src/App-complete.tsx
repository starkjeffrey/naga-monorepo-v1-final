/**
 * Complete Professional SIS Dashboard with Header, Sidebar, Footer, and Main Area
 */

import React from 'react';

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
    backgroundColor: '#1d4ed8',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    color: 'white',
  },
  brandInfo: {},
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
  headerRight: {
    textAlign: 'right' as const,
  },
  signOutBtn: {
    backgroundColor: '#ef4444',
    color: 'white',
    border: 'none',
    padding: '0.5rem 1rem',
    borderRadius: '6px',
    cursor: 'pointer',
    fontSize: '0.875rem',
    fontWeight: '500',
    marginLeft: '1rem',
  },
  layout: {
    display: 'flex',
    height: 'calc(100vh - 73px)', // Subtract header height
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
  navList: {
    display: 'flex',
    flexDirection: 'column' as const,
    gap: '0.5rem',
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
    backgroundColor: '#1d4ed8',
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
    gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))',
    gap: '1.5rem',
    marginBottom: '2rem',
  },
  card: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    border: '1px solid #e5e7eb',
    padding: '1.5rem',
  },
  cardHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    marginBottom: '1rem',
  },
  cardIcon: {
    width: '48px',
    height: '48px',
    borderRadius: '8px',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
  },
  cardTitle: {
    fontSize: '0.875rem',
    fontWeight: '500',
    color: '#6b7280',
    margin: 0,
  },
  cardValue: {
    fontSize: '1.875rem',
    fontWeight: 'bold',
    marginTop: '0.25rem',
    margin: 0,
  },
  cardChange: {
    display: 'flex',
    alignItems: 'center',
    fontSize: '0.875rem',
    marginTop: '1rem',
  },
  changeUp: {
    color: '#059669',
    fontWeight: '500',
    marginRight: '0.5rem',
  },
  changeText: {
    color: '#6b7280',
  },
  twoColGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '2rem',
    '@media (max-width: 1024px)': {
      gridTemplateColumns: '1fr',
    },
  },
  section: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
    border: '1px solid #e5e7eb',
  },
  sectionHeader: {
    padding: '1.5rem',
    borderBottom: '1px solid #e5e7eb',
  },
  sectionTitle: {
    fontSize: '1.125rem',
    fontWeight: '600',
    color: '#111827',
    margin: 0,
    marginBottom: '0.25rem',
  },
  sectionSubtitle: {
    fontSize: '0.875rem',
    color: '#6b7280',
    margin: 0,
  },
  sectionContent: {
    padding: '1.5rem',
  },
  termItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '1rem',
    borderRadius: '8px',
    marginBottom: '1rem',
  },
  termInfo: {
    flex: 1,
  },
  termName: {
    fontWeight: '600',
    color: '#111827',
    margin: 0,
    marginBottom: '0.25rem',
  },
  termDate: {
    fontSize: '0.875rem',
    color: '#6b7280',
    margin: 0,
  },
  termStats: {
    textAlign: 'right' as const,
  },
  termValue: {
    fontSize: '1.5rem',
    fontWeight: 'bold',
    margin: 0,
  },
  termLabel: {
    fontSize: '0.875rem',
    color: '#6b7280',
    margin: 0,
  },
  footer: {
    backgroundColor: '#ffffff',
    borderTop: '1px solid #e5e7eb',
    padding: '1rem 2rem',
    marginTop: '2rem',
  },
  footerContent: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    fontSize: '0.875rem',
    color: '#6b7280',
  },
  footerStatus: {
    color: '#059669',
    fontWeight: '500',
  },
};

function App() {
  const currentDate = new Date().toLocaleDateString('en-US', {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  });

  const lastUpdated = new Date().toLocaleTimeString('en-US', {
    hour: '2-digit',
    minute: '2-digit'
  });

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
          <div style={styles.headerLeft}>
            <div style={styles.logo}>
              <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z" />
              </svg>
            </div>
            <div style={styles.brandInfo}>
              <h1 style={styles.title}>NAGA SIS</h1>
              <p style={styles.subtitle}>Student Information System</p>
            </div>
          </div>
          <div style={styles.headerRight}>
            <div>
              <p style={{...styles.subtitle, fontWeight: '500', color: '#111827'}}>Academic Dashboard</p>
              <p style={styles.subtitle}>{currentDate}</p>
            </div>
            <button style={styles.signOutBtn}>Sign Out</button>
          </div>
        </div>
      </header>

      <div style={styles.layout}>
        {/* Sidebar */}
        <aside style={styles.sidebar}>
          <nav style={styles.sidebarNav}>
            <div style={styles.navList}>
              <div style={{...styles.navItem, ...styles.navItemActive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Dashboard</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
                <span>Students</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                </svg>
                <span>Schedule</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                <span>Testing</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
                <span>Curriculum</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
                <span>Reports</span>
              </div>
              <div style={{...styles.navItem, ...styles.navItemInactive}}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
                <span>Settings</span>
              </div>
            </div>
          </nav>
        </aside>

        {/* Main Content */}
        <main style={styles.main}>
          {/* Page Title */}
          <div style={styles.pageTitle}>
            <h2 style={styles.pageTitleH2}>Academic Dashboard</h2>
            <p style={styles.pageTitleP}>Overview of current academic activities and enrollment</p>
          </div>

          {/* Key Metrics */}
          <div style={styles.grid}>
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Testees This Week</p>
                  <p style={{...styles.cardValue, color: '#1d4ed8'}}>142</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#dbeafe'}}>
                  <svg width="24" height="24" fill="none" stroke="#1d4ed8" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeUp}>↗ +23%</span>
                <span style={styles.changeText}>vs last week</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Active Students</p>
                  <p style={{...styles.cardValue, color: '#059669'}}>1,847</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#d1fae5'}}>
                  <svg width="24" height="24" fill="none" stroke="#059669" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeUp}>↗ +5.2%</span>
                <span style={styles.changeText}>this term</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Active Classes</p>
                  <p style={{...styles.cardValue, color: '#d97706'}}>89</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#fef3c7'}}>
                  <svg width="24" height="24" fill="none" stroke="#d97706" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeText}>across all levels</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Pending Enrollments</p>
                  <p style={{...styles.cardValue, color: '#7c3aed'}}>37</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#ede9fe'}}>
                  <svg width="24" height="24" fill="none" stroke="#7c3aed" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={{color: '#7c3aed', fontWeight: '500'}}>requires review</span>
              </div>
            </div>
          </div>

          {/* Two Column Layout */}
          <div style={styles.twoColGrid}>
            {/* Students by Term */}
            <div style={styles.section}>
              <div style={styles.sectionHeader}>
                <h3 style={styles.sectionTitle}>Students by Term</h3>
                <p style={styles.sectionSubtitle}>Current enrollment breakdown</p>
              </div>
              <div style={styles.sectionContent}>
                <div style={{...styles.termItem, backgroundColor: '#dbeafe'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Fall 2024 (Current)</p>
                    <p style={styles.termDate}>Sep 1 - Dec 15, 2024</p>
                  </div>
                  <div style={styles.termStats}>
                    <p style={{...styles.termValue, color: '#1d4ed8'}}>1,247</p>
                    <p style={styles.termLabel}>students</p>
                  </div>
                </div>

                <div style={{...styles.termItem, backgroundColor: '#d1fae5'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Winter 2025 (Next)</p>
                    <p style={styles.termDate}>Jan 6 - Apr 20, 2025</p>
                  </div>
                  <div style={styles.termStats}>
                    <p style={{...styles.termValue, color: '#059669'}}>389</p>
                    <p style={styles.termLabel}>enrolled</p>
                  </div>
                </div>

                <div style={{...styles.termItem, backgroundColor: '#fef3c7'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Spring 2025</p>
                    <p style={styles.termDate}>May 1 - Aug 15, 2025</p>
                  </div>
                  <div style={styles.termStats}>
                    <p style={{...styles.termValue, color: '#d97706'}}>211</p>
                    <p style={styles.termLabel}>pre-enrolled</p>
                  </div>
                </div>
              </div>
            </div>

            {/* Key Dates */}
            <div style={styles.section}>
              <div style={styles.sectionHeader}>
                <h3 style={styles.sectionTitle}>Upcoming Key Dates</h3>
                <p style={styles.sectionSubtitle}>Important academic deadlines</p>
              </div>
              <div style={styles.sectionContent}>
                <div style={{...styles.termItem, backgroundColor: '#fef2f2', borderLeft: '4px solid #f87171'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Fall Term End</p>
                    <p style={styles.termDate}>December 15, 2024</p>
                    <p style={{fontSize: '0.75rem', color: '#dc2626', margin: 0}}>3 weeks remaining</p>
                  </div>
                </div>

                <div style={{...styles.termItem, backgroundColor: '#eff6ff', borderLeft: '4px solid #3b82f6'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Winter Registration Opens</p>
                    <p style={styles.termDate}>December 1, 2024</p>
                    <p style={{fontSize: '0.75rem', color: '#2563eb', margin: 0}}>Opens in 1 week</p>
                  </div>
                </div>

                <div style={{...styles.termItem, backgroundColor: '#f0fdf4', borderLeft: '4px solid #22c55e'}}>
                  <div style={styles.termInfo}>
                    <p style={styles.termName}>Winter Term Begins</p>
                    <p style={styles.termDate}>January 6, 2025</p>
                    <p style={{fontSize: '0.75rem', color: '#16a34a', margin: 0}}>6 weeks away</p>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Footer */}
          <footer style={styles.footer}>
            <div style={styles.footerContent}>
              <p>© 2024 NAGA School. All rights reserved.</p>
              <div style={{display: 'flex', alignItems: 'center', gap: '1.5rem'}}>
                <span>System Status: <span style={styles.footerStatus}>Operational</span></span>
                <span>Last Updated: <span>{lastUpdated}</span></span>
              </div>
            </div>
          </footer>
        </main>
      </div>
    </div>
  );
}

export default App;