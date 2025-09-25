/**
 * Demo App - Switch between Regular Dashboard, Admin Panel, and Dual List
 */

import React, { useState } from 'react';
import DualListDemo from './DualListDemo';

// Import both dashboard components (we'll inline them here for simplicity)
const RegularDashboard = () => {
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
      display: 'flex',
      alignItems: 'center',
      gap: '1rem',
    },
    demoToggle: {
      backgroundColor: '#1d4ed8',
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

  return (
    <div style={styles.app}>
      {/* Header */}
      <header style={styles.header}>
        <div style={styles.headerContent}>
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
            <div style={{textAlign: 'right' as const}}>
              <p style={{...styles.subtitle, fontWeight: '500', color: '#111827'}}>Academic Dashboard</p>
              <p style={styles.subtitle}>{currentDate}</p>
            </div>
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
          <div style={styles.pageTitle}>
            <h2 style={styles.pageTitleH2}>Academic Dashboard</h2>
            <p style={styles.pageTitleP}>Overview of current academic activities and enrollment</p>
          </div>

          {/* Key Metrics */}
          <div style={styles.grid}>
            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Active Classes</p>
                  <p style={{...styles.cardValue, color: '#1d4ed8'}}>24</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#dbeafe'}}>
                  <svg width="24" height="24" fill="none" stroke="#1d4ed8" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.746 0 3.332.477 4.5 1.253v13C19.832 18.477 18.246 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeUp}>+2 new classes</span>
                <span style={styles.changeText}>this week</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Total Enrollments</p>
                  <p style={{...styles.cardValue, color: '#059669'}}>347</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#d1fae5'}}>
                  <svg width="24" height="24" fill="none" stroke="#059669" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeUp}>↗ +15</span>
                <span style={styles.changeText}>new this week</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Class Capacity</p>
                  <p style={{...styles.cardValue, color: '#d97706'}}>78%</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#fef3c7'}}>
                  <svg width="24" height="24" fill="none" stroke="#d97706" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={styles.changeText}>average utilization</span>
              </div>
            </div>

            <div style={styles.card}>
              <div style={styles.cardHeader}>
                <div>
                  <p style={styles.cardTitle}>Pending Enrollments</p>
                  <p style={{...styles.cardValue, color: '#7c3aed'}}>12</p>
                </div>
                <div style={{...styles.cardIcon, backgroundColor: '#ede9fe'}}>
                  <svg width="24" height="24" fill="none" stroke="#7c3aed" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                </div>
              </div>
              <div style={styles.cardChange}>
                <span style={{color: '#7c3aed', fontWeight: '500'}}>awaiting approval</span>
              </div>
            </div>
          </div>

          {/* Classes and Enrollments */}
          <div style={{
            display: 'grid',
            gridTemplateColumns: '1fr 1fr',
            gap: '2rem',
            marginBottom: '2rem',
            '@media (max-width: 1024px)': {
              gridTemplateColumns: '1fr',
            },
          }}>
            {/* Current Classes */}
            <div style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
              border: '1px solid #e5e7eb',
            }}>
              <div style={{padding: '1.5rem', borderBottom: '1px solid #e5e7eb'}}>
                <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0, marginBottom: '0.25rem'}}>Current Classes</h3>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Active classes this term</p>
              </div>
              <div style={{padding: '1.5rem'}}>
                <div style={{display: 'flex', flexDirection: 'column', gap: '1rem'}}>
                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#f0f9ff', borderRadius: '8px'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>ESL Beginner A</p>
                      <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Mon/Wed/Fri 9:00-11:00 AM</p>
                    </div>
                    <div style={{textAlign: 'right'}}>
                      <p style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#1d4ed8', margin: 0}}>18/20</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>enrolled</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#f0fdf4', borderRadius: '8px'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>ESL Intermediate B</p>
                      <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Tue/Thu 10:00-12:00 PM</p>
                    </div>
                    <div style={{textAlign: 'right'}}>
                      <p style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#059669', margin: 0}}>15/16</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>enrolled</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#fffbeb', borderRadius: '8px'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>ESL Advanced C</p>
                      <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Mon/Wed/Fri 2:00-4:00 PM</p>
                    </div>
                    <div style={{textAlign: 'right'}}>
                      <p style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#d97706', margin: 0}}>12/15</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>enrolled</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#f5f3ff', borderRadius: '8px'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>Business English</p>
                      <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Sat 9:00 AM-1:00 PM</p>
                    </div>
                    <div style={{textAlign: 'right'}}>
                      <p style={{fontSize: '1.25rem', fontWeight: 'bold', color: '#7c3aed', margin: 0}}>8/12</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>enrolled</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Recent Enrollments */}
            <div style={{
              backgroundColor: '#ffffff',
              borderRadius: '8px',
              boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
              border: '1px solid #e5e7eb',
            }}>
              <div style={{padding: '1.5rem', borderBottom: '1px solid #e5e7eb'}}>
                <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0, marginBottom: '0.25rem'}}>Recent Enrollments</h3>
                <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Latest student enrollments</p>
              </div>
              <div style={{padding: '1.5rem'}}>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', backgroundColor: '#f0f9ff', borderRadius: '6px'}}>
                    <div style={{width: '8px', height: '8px', backgroundColor: '#1d4ed8', borderRadius: '50%', flexShrink: 0}}></div>
                    <div style={{flex: 1}}>
                      <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', margin: 0}}>Sarah Chen enrolled in ESL Beginner A</p>
                      <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>2 hours ago</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', backgroundColor: '#f0fdf4', borderRadius: '6px'}}>
                    <div style={{width: '8px', height: '8px', backgroundColor: '#059669', borderRadius: '50%', flexShrink: 0}}></div>
                    <div style={{flex: 1}}>
                      <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', margin: 0}}>Miguel Rodriguez enrolled in Business English</p>
                      <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>4 hours ago</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', backgroundColor: '#fffbeb', borderRadius: '6px'}}>
                    <div style={{width: '8px', height: '8px', backgroundColor: '#d97706', borderRadius: '50%', flexShrink: 0}}></div>
                    <div style={{flex: 1}}>
                      <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', margin: 0}}>Anna Kowalski enrolled in ESL Intermediate B</p>
                      <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>6 hours ago</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', backgroundColor: '#f5f3ff', borderRadius: '6px'}}>
                    <div style={{width: '8px', height: '8px', backgroundColor: '#7c3aed', borderRadius: '50%', flexShrink: 0}}></div>
                    <div style={{flex: 1}}>
                      <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', margin: 0}}>David Park enrolled in ESL Advanced C</p>
                      <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>1 day ago</p>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', gap: '0.75rem', padding: '0.75rem', backgroundColor: '#fef2f2', borderRadius: '6px'}}>
                    <div style={{width: '8px', height: '8px', backgroundColor: '#ef4444', borderRadius: '50%', flexShrink: 0}}></div>
                    <div style={{flex: 1}}>
                      <p style={{fontSize: '0.875rem', fontWeight: '500', color: '#374151', margin: 0}}>Lisa Thompson - enrollment pending approval</p>
                      <p style={{fontSize: '0.75rem', color: '#9ca3af', margin: 0}}>1 day ago</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>

          {/* Upcoming Terms & Key Dates */}
          <div style={{
            backgroundColor: '#ffffff',
            borderRadius: '8px',
            boxShadow: '0 1px 3px 0 rgba(0, 0, 0, 0.1)',
            border: '1px solid #e5e7eb',
            marginBottom: '2rem',
          }}>
            <div style={{padding: '1.5rem', borderBottom: '1px solid #e5e7eb'}}>
              <h3 style={{fontSize: '1.125rem', fontWeight: '600', color: '#111827', margin: 0, marginBottom: '0.25rem'}}>2025-2026 Academic Year</h3>
              <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Upcoming term dates and registration deadlines</p>
            </div>
            <div style={{padding: '1.5rem'}}>
              <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1rem'}}>
                <div style={{padding: '1rem', backgroundColor: '#f0f9ff', borderRadius: '8px', border: '1px solid #0ea5e9'}}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.5rem'}}>
                    <div style={{width: '12px', height: '12px', backgroundColor: '#0ea5e9', borderRadius: '50%', marginRight: '0.5rem'}}></div>
                    <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>Winter 2025</h4>
                  </div>
                  <p style={{fontSize: '0.875rem', color: '#374151', margin: '0 0 0.25rem 0'}}>January 13 - April 11, 2025</p>
                  <p style={{fontSize: '0.75rem', color: '#0ea5e9', fontWeight: '500', margin: 0}}>Registration: December 16 - January 10</p>
                </div>

                <div style={{padding: '1rem', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #22c55e'}}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.5rem'}}>
                    <div style={{width: '12px', height: '12px', backgroundColor: '#22c55e', borderRadius: '50%', marginRight: '0.5rem'}}></div>
                    <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>Spring 2025</h4>
                  </div>
                  <p style={{fontSize: '0.875rem', color: '#374151', margin: '0 0 0.25rem 0'}}>April 21 - July 18, 2025</p>
                  <p style={{fontSize: '0.75rem', color: '#22c55e', fontWeight: '500', margin: 0}}>Registration: March 24 - April 18</p>
                </div>

                <div style={{padding: '1rem', backgroundColor: '#fefce8', borderRadius: '8px', border: '1px solid #eab308'}}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.5rem'}}>
                    <div style={{width: '12px', height: '12px', backgroundColor: '#eab308', borderRadius: '50%', marginRight: '0.5rem'}}></div>
                    <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>Fall 2025</h4>
                  </div>
                  <p style={{fontSize: '0.875rem', color: '#374151', margin: '0 0 0.25rem 0'}}>September 8 - December 13, 2025</p>
                  <p style={{fontSize: '0.75rem', color: '#eab308', fontWeight: '500', margin: 0}}>Registration: August 11 - September 5</p>
                </div>

                <div style={{padding: '1rem', backgroundColor: '#fdf2f8', borderRadius: '8px', border: '1px solid #ec4899'}}>
                  <div style={{display: 'flex', alignItems: 'center', marginBottom: '0.5rem'}}>
                    <div style={{width: '12px', height: '12px', backgroundColor: '#ec4899', borderRadius: '50%', marginRight: '0.5rem'}}></div>
                    <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: 0}}>Winter 2026</h4>
                  </div>
                  <p style={{fontSize: '0.875rem', color: '#374151', margin: '0 0 0.25rem 0'}}>January 12 - April 10, 2026</p>
                  <p style={{fontSize: '0.75rem', color: '#ec4899', fontWeight: '500', margin: 0}}>Registration: December 15 - January 9</p>
                </div>
              </div>
            </div>
          </div>

          <footer style={styles.footer}>
            <div style={styles.footerContent}>
              <p>© 2025 NAGA School. All rights reserved.</p>
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
};

const AdminPanel = ({ onSwitchToRegular }: { onSwitchToRegular: () => void }) => {
  // Just showing key admin features for demo
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
    switchBtn: {
      backgroundColor: '#1d4ed8',
      color: 'white',
      border: 'none',
      padding: '0.5rem 1rem',
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.875rem',
      fontWeight: '500',
    },
    main: {
      padding: '2rem',
    },
    pageTitle: {
      marginBottom: '2rem',
      textAlign: 'center' as const,
    },
    pageTitleH2: {
      fontSize: '2rem',
      fontWeight: 'bold',
      color: '#111827',
      margin: 0,
      marginBottom: '0.5rem',
    },
    adminGrid: {
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))',
      gap: '1.5rem',
      maxWidth: '1200px',
      margin: '0 auto',
    },
    adminCard: {
      backgroundColor: '#ffffff',
      borderRadius: '12px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      border: '1px solid #e5e7eb',
      padding: '2rem',
      textAlign: 'center' as const,
    },
    adminIcon: {
      width: '64px',
      height: '64px',
      borderRadius: '12px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      margin: '0 auto 1rem auto',
    },
    adminTitle: {
      fontSize: '1.25rem',
      fontWeight: '600',
      color: '#111827',
      margin: '0 0 0.5rem 0',
    },
    adminDesc: {
      fontSize: '0.875rem',
      color: '#6b7280',
      margin: 0,
      lineHeight: '1.5',
    },
  };

  return (
    <div style={styles.app}>
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
          <button style={styles.switchBtn} onClick={onSwitchToRegular}>
            Switch to Regular Dashboard
          </button>
        </div>
      </header>

      <main style={styles.main}>
        <div style={styles.pageTitle}>
          <h2 style={styles.pageTitleH2}>Administrator Dashboard</h2>
          <p style={{color: '#6b7280', fontSize: '1.125rem'}}>Manage system settings, users, and monitor activity</p>
        </div>

        {/* Class Management Section */}
        <div style={{
          backgroundColor: '#ffffff',
          borderRadius: '12px',
          boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
          border: '1px solid #e5e7eb',
          marginBottom: '2rem',
        }}>
          <div style={{padding: '1.5rem', borderBottom: '1px solid #e5e7eb'}}>
            <h3 style={{fontSize: '1.25rem', fontWeight: '600', color: '#111827', margin: 0, marginBottom: '0.25rem'}}>Class Management</h3>
            <p style={{fontSize: '0.875rem', color: '#6b7280', margin: 0}}>Create, edit, and manage class schedules and enrollment</p>
          </div>
          <div style={{padding: '1.5rem'}}>
            <div style={{display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1rem', marginBottom: '1.5rem'}}>
              <button style={{
                backgroundColor: '#1d4ed8',
                color: 'white',
                border: 'none',
                padding: '1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
                </svg>
                Create New Class
              </button>
              <button style={{
                backgroundColor: '#059669',
                color: 'white',
                border: 'none',
                padding: '1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0V3a2 2 0 012-2h4a2 2 0 012 2v4m-6 0h8m-9 0H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5z" />
                </svg>
                Manage Schedules
              </button>
              <button style={{
                backgroundColor: '#d97706',
                color: 'white',
                border: 'none',
                padding: '1rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '500',
                display: 'flex',
                alignItems: 'center',
                gap: '0.5rem',
              }}>
                <svg width="20" height="20" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
                </svg>
                Bulk Enrollment
              </button>
            </div>

            {/* Current Classes Management */}
            <div style={{display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem'}}>
              <div>
                <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: '0 0 1rem 0'}}>Active Classes</h4>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#f0f9ff', borderRadius: '8px', border: '1px solid #e0f2fe'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>ESL Beginner A</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Mon/Wed/Fri 9:00-11:00 AM • Room 101</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#1d4ed8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Edit</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>18/20</button>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#f0fdf4', borderRadius: '8px', border: '1px solid #dcfce7'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>ESL Intermediate B</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Tue/Thu 10:00-12:00 PM • Room 102</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#1d4ed8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Edit</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>15/16</button>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#fffbeb', borderRadius: '8px', border: '1px solid #fef3c7'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>Business English</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Saturday 9:00 AM-1:00 PM • Room 201</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#1d4ed8', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Edit</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#d97706', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>8/12</button>
                    </div>
                  </div>
                </div>
              </div>

              <div>
                <h4 style={{fontSize: '1rem', fontWeight: '600', color: '#111827', margin: '0 0 1rem 0'}}>Enrollment Requests</h4>
                <div style={{display: 'flex', flexDirection: 'column', gap: '0.75rem'}}>
                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#fef2f2', borderRadius: '8px', border: '1px solid #fecaca'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>Sarah Chen → ESL Beginner A</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Requested 2 hours ago</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Approve</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#dc2626', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Deny</button>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#fef2f2', borderRadius: '8px', border: '1px solid #fecaca'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>Lisa Thompson → Business English</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Requested 1 day ago</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Approve</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#dc2626', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Deny</button>
                    </div>
                  </div>

                  <div style={{display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '1rem', backgroundColor: '#fef2f2', borderRadius: '8px', border: '1px solid #fecaca'}}>
                    <div>
                      <p style={{fontWeight: '600', color: '#111827', margin: 0}}>Mike Johnson → ESL Advanced C</p>
                      <p style={{fontSize: '0.75rem', color: '#6b7280', margin: 0}}>Requested 1 day ago</p>
                    </div>
                    <div style={{display: 'flex', gap: '0.5rem'}}>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#059669', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Approve</button>
                      <button style={{padding: '0.25rem 0.5rem', fontSize: '0.75rem', backgroundColor: '#dc2626', color: 'white', border: 'none', borderRadius: '4px', cursor: 'pointer'}}>Deny</button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div style={styles.adminGrid}>
          <div style={styles.adminCard}>
            <div style={{...styles.adminIcon, backgroundColor: '#dbeafe'}}>
              <svg width="32" height="32" fill="none" stroke="#1d4ed8" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197m13.5-9a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0z" />
              </svg>
            </div>
            <h3 style={styles.adminTitle}>Staff Management</h3>
            <p style={styles.adminDesc}>
              Manage instructor assignments, permissions, and staff schedules.
              <br/><strong>12 active instructors</strong>
            </p>
          </div>

          <div style={styles.adminCard}>
            <div style={{...styles.adminIcon, backgroundColor: '#d1fae5'}}>
              <svg width="32" height="32" fill="none" stroke="#059669" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
            </div>
            <h3 style={styles.adminTitle}>Class Reports</h3>
            <p style={styles.adminDesc}>
              Generate attendance, enrollment, and performance reports by class.
              <br/><strong>8 reports available</strong>
            </p>
          </div>
        </div>
      </main>
    </div>
  );
};

function App() {
  const [viewMode, setViewMode] = useState<'regular' | 'admin' | 'duallist'>('regular');

  if (viewMode === 'duallist') {
    return <DualListDemo onBack={() => setViewMode('regular')} />;
  }

  return (
    <>
      {viewMode === 'regular' ? (
        <div>
          <RegularDashboard />
          <div style={{
            position: 'fixed',
            top: '20px',
            right: '20px',
            zIndex: 1000,
            display: 'flex',
            flexDirection: 'column',
            gap: '0.5rem',
          }}>
            <button
              style={{
                backgroundColor: '#dc2626',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '600',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              onClick={() => setViewMode('admin')}
            >
              🔧 Admin View
            </button>
            <button
              style={{
                backgroundColor: '#7c3aed',
                color: 'white',
                border: 'none',
                padding: '0.75rem 1.5rem',
                borderRadius: '8px',
                cursor: 'pointer',
                fontSize: '0.875rem',
                fontWeight: '600',
                boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
              }}
              onClick={() => setViewMode('duallist')}
            >
              📋 Enrollment Tool
            </button>
          </div>
        </div>
      ) : (
        <AdminPanel onSwitchToRegular={() => setViewMode('regular')} />
      )}
    </>
  );
}

export default App;