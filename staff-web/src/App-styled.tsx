/**
 * Professional SIS Dashboard with inline styles (no Tailwind dependency)
 */

import React from 'react';

const styles = {
  container: {
    minHeight: '100vh',
    backgroundColor: '#f9fafb',
    padding: '2rem',
    fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
  },
  maxWidth: {
    maxWidth: '1200px',
    margin: '0 auto',
  },
  header: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1), 0 1px 2px 0 rgba(0, 0, 0, 0.06)',
    padding: '1.5rem',
    marginBottom: '2rem',
  },
  headerFlex: {
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
  section: {
    backgroundColor: '#ffffff',
    borderRadius: '8px',
    boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
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
    marginTop: '2rem',
    textAlign: 'center' as const,
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

  return (
    <div style={styles.container}>
      <div style={styles.maxWidth}>
        <header style={styles.header}>
          <div style={styles.headerFlex}>
            <div style={styles.headerLeft}>
              <div style={styles.logo}>
                <svg width="24" height="24" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 14l9-5-9-5-9 5 9 5z" />
                </svg>
              </div>
              <div>
                <h1 style={styles.title}>NAGA SIS</h1>
                <p style={styles.subtitle}>Student Information System</p>
              </div>
            </div>
            <div style={styles.headerRight}>
              <p style={styles.title}>Academic Dashboard</p>
              <p style={styles.subtitle}>{currentDate}</p>
            </div>
          </div>
        </header>

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

        <footer style={styles.footer}>
          <p>© 2024 NAGA School - System Status: <span style={styles.footerStatus}>Operational</span></p>
        </footer>
      </div>
    </div>
  );
}

export default App;