/**
 * Dual List Transfer Demo - Simple version with inline styles
 */

import React, { useState } from 'react';

interface TransferItem {
  id: string;
  name: string;
  email?: string;
  studentId?: string;
}

const DualListDemo: React.FC<{ onBack: () => void }> = ({ onBack }) => {
  const [availableItems, setAvailableItems] = useState<TransferItem[]>([
    { id: '1', name: 'Alice Johnson', email: 'alice@example.com', studentId: 'ST001' },
    { id: '2', name: 'Bob Smith', email: 'bob@example.com', studentId: 'ST002' },
    { id: '3', name: 'Charlie Brown', email: 'charlie@example.com', studentId: 'ST003' },
    { id: '4', name: 'Diana Prince', email: 'diana@example.com', studentId: 'ST004' },
    { id: '5', name: 'Edward Norton', email: 'edward@example.com', studentId: 'ST005' },
    { id: '6', name: 'Fiona Green', email: 'fiona@example.com', studentId: 'ST006' },
  ]);

  const [enrolledItems, setEnrolledItems] = useState<TransferItem[]>([
    { id: '7', name: 'George Wilson', email: 'george@example.com', studentId: 'ST007' },
    { id: '8', name: 'Hannah Davis', email: 'hannah@example.com', studentId: 'ST008' },
  ]);

  const [selectedAvailable, setSelectedAvailable] = useState<string[]>([]);
  const [selectedEnrolled, setSelectedEnrolled] = useState<string[]>([]);

  const styles = {
    container: {
      minHeight: '100vh',
      backgroundColor: '#f9fafb',
      padding: '2rem',
      fontFamily: '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif',
    },
    header: {
      textAlign: 'center' as const,
      marginBottom: '2rem',
    },
    title: {
      fontSize: '2rem',
      fontWeight: 'bold',
      color: '#111827',
      margin: '0 0 0.5rem 0',
    },
    subtitle: {
      fontSize: '1.125rem',
      color: '#6b7280',
      margin: 0,
    },
    backBtn: {
      position: 'fixed' as const,
      top: '20px',
      left: '20px',
      backgroundColor: '#6b7280',
      color: 'white',
      border: 'none',
      padding: '0.75rem 1.5rem',
      borderRadius: '8px',
      cursor: 'pointer',
      fontSize: '0.875rem',
      fontWeight: '600',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
    },
    transferContainer: {
      maxWidth: '1200px',
      margin: '0 auto',
      backgroundColor: '#ffffff',
      borderRadius: '12px',
      boxShadow: '0 4px 6px -1px rgba(0, 0, 0, 0.1)',
      padding: '2rem',
    },
    transferLayout: {
      display: 'grid',
      gridTemplateColumns: '1fr auto 1fr',
      gap: '2rem',
      alignItems: 'start',
    },
    listContainer: {
      border: '1px solid #e5e7eb',
      borderRadius: '8px',
      backgroundColor: '#ffffff',
      minHeight: '400px',
    },
    listHeader: {
      backgroundColor: '#f9fafb',
      padding: '1rem',
      borderBottom: '1px solid #e5e7eb',
      borderRadius: '8px 8px 0 0',
    },
    listTitle: {
      fontSize: '1rem',
      fontWeight: '600',
      color: '#111827',
      margin: '0 0 0.5rem 0',
    },
    listCount: {
      fontSize: '0.875rem',
      color: '#6b7280',
      margin: 0,
    },
    listContent: {
      padding: '1rem',
      maxHeight: '300px',
      overflowY: 'auto' as const,
    },
    listItem: {
      display: 'flex',
      alignItems: 'center',
      padding: '0.75rem',
      borderRadius: '6px',
      cursor: 'pointer',
      marginBottom: '0.5rem',
      transition: 'all 0.2s',
      border: '1px solid transparent',
    },
    listItemHover: {
      backgroundColor: '#f3f4f6',
    },
    listItemSelected: {
      backgroundColor: '#dbeafe',
      border: '1px solid #3b82f6',
    },
    checkbox: {
      marginRight: '0.75rem',
    },
    itemInfo: {
      flex: 1,
    },
    itemName: {
      fontSize: '0.875rem',
      fontWeight: '500',
      color: '#111827',
      margin: '0 0 0.25rem 0',
    },
    itemDetails: {
      fontSize: '0.75rem',
      color: '#6b7280',
      margin: 0,
    },
    controlsContainer: {
      display: 'flex',
      flexDirection: 'column' as const,
      gap: '0.5rem',
      alignSelf: 'center',
    },
    controlBtn: {
      backgroundColor: '#1d4ed8',
      color: 'white',
      border: 'none',
      padding: '0.75rem 1rem',
      borderRadius: '6px',
      cursor: 'pointer',
      fontSize: '0.875rem',
      fontWeight: '500',
      minWidth: '100px',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      gap: '0.5rem',
    },
    controlBtnDisabled: {
      backgroundColor: '#d1d5db',
      cursor: 'not-allowed',
    },
    stats: {
      marginTop: '2rem',
      textAlign: 'center' as const,
      padding: '1rem',
      backgroundColor: '#f9fafb',
      borderRadius: '8px',
    },
  };

  const moveToEnrolled = () => {
    const itemsToMove = availableItems.filter(item => selectedAvailable.includes(item.id));
    setEnrolledItems([...enrolledItems, ...itemsToMove]);
    setAvailableItems(availableItems.filter(item => !selectedAvailable.includes(item.id)));
    setSelectedAvailable([]);
  };

  const moveToAvailable = () => {
    const itemsToMove = enrolledItems.filter(item => selectedEnrolled.includes(item.id));
    setAvailableItems([...availableItems, ...itemsToMove]);
    setEnrolledItems(enrolledItems.filter(item => !selectedEnrolled.includes(item.id)));
    setSelectedEnrolled([]);
  };

  const moveAllToEnrolled = () => {
    setEnrolledItems([...enrolledItems, ...availableItems]);
    setAvailableItems([]);
    setSelectedAvailable([]);
  };

  const moveAllToAvailable = () => {
    setAvailableItems([...availableItems, ...enrolledItems]);
    setEnrolledItems([]);
    setSelectedEnrolled([]);
  };

  const handleAvailableSelect = (itemId: string) => {
    setSelectedAvailable(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  const handleEnrolledSelect = (itemId: string) => {
    setSelectedEnrolled(prev =>
      prev.includes(itemId)
        ? prev.filter(id => id !== itemId)
        : [...prev, itemId]
    );
  };

  return (
    <div style={styles.container}>
      <button style={styles.backBtn} onClick={onBack}>
        ← Back to Dashboard
      </button>

      <div style={styles.header}>
        <h1 style={styles.title}>Student Enrollment Management</h1>
        <p style={styles.subtitle}>Transfer students between available and enrolled lists</p>
      </div>

      <div style={styles.transferContainer}>
        <div style={styles.transferLayout}>
          {/* Available Students */}
          <div style={styles.listContainer}>
            <div style={styles.listHeader}>
              <h3 style={styles.listTitle}>Available Students</h3>
              <p style={styles.listCount}>{availableItems.length} students available</p>
            </div>
            <div style={styles.listContent}>
              {availableItems.map((item) => (
                <div
                  key={item.id}
                  style={{
                    ...styles.listItem,
                    ...(selectedAvailable.includes(item.id) ? styles.listItemSelected : {}),
                  }}
                  onClick={() => handleAvailableSelect(item.id)}
                >
                  <input
                    type="checkbox"
                    checked={selectedAvailable.includes(item.id)}
                    onChange={() => handleAvailableSelect(item.id)}
                    style={styles.checkbox}
                  />
                  <div style={styles.itemInfo}>
                    <p style={styles.itemName}>{item.name}</p>
                    <p style={styles.itemDetails}>
                      {item.email} • ID: {item.studentId}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Transfer Controls */}
          <div style={styles.controlsContainer}>
            <button
              style={{
                ...styles.controlBtn,
                ...(availableItems.length === 0 ? styles.controlBtnDisabled : {}),
              }}
              onClick={moveAllToEnrolled}
              disabled={availableItems.length === 0}
            >
              <span>≫</span>
            </button>
            <button
              style={{
                ...styles.controlBtn,
                ...(selectedAvailable.length === 0 ? styles.controlBtnDisabled : {}),
              }}
              onClick={moveToEnrolled}
              disabled={selectedAvailable.length === 0}
            >
              <span>→</span>
            </button>
            <button
              style={{
                ...styles.controlBtn,
                ...(selectedEnrolled.length === 0 ? styles.controlBtnDisabled : {}),
              }}
              onClick={moveToAvailable}
              disabled={selectedEnrolled.length === 0}
            >
              <span>←</span>
            </button>
            <button
              style={{
                ...styles.controlBtn,
                ...(enrolledItems.length === 0 ? styles.controlBtnDisabled : {}),
              }}
              onClick={moveAllToAvailable}
              disabled={enrolledItems.length === 0}
            >
              <span>≪</span>
            </button>
          </div>

          {/* Enrolled Students */}
          <div style={styles.listContainer}>
            <div style={styles.listHeader}>
              <h3 style={styles.listTitle}>Enrolled Students</h3>
              <p style={styles.listCount}>{enrolledItems.length} students enrolled</p>
            </div>
            <div style={styles.listContent}>
              {enrolledItems.map((item) => (
                <div
                  key={item.id}
                  style={{
                    ...styles.listItem,
                    ...(selectedEnrolled.includes(item.id) ? styles.listItemSelected : {}),
                  }}
                  onClick={() => handleEnrolledSelect(item.id)}
                >
                  <input
                    type="checkbox"
                    checked={selectedEnrolled.includes(item.id)}
                    onChange={() => handleEnrolledSelect(item.id)}
                    style={styles.checkbox}
                  />
                  <div style={styles.itemInfo}>
                    <p style={styles.itemName}>{item.name}</p>
                    <p style={styles.itemDetails}>
                      {item.email} • ID: {item.studentId}
                    </p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        <div style={styles.stats}>
          <p style={{color: '#374151', fontSize: '0.875rem'}}>
            <strong>Transfer Summary:</strong> {availableItems.length} available, {enrolledItems.length} enrolled
            {selectedAvailable.length > 0 && ` • ${selectedAvailable.length} selected to enroll`}
            {selectedEnrolled.length > 0 && ` • ${selectedEnrolled.length} selected to remove`}
          </p>
        </div>
      </div>
    </div>
  );
};

export default DualListDemo;