import React from 'react';

const DebugDemographics: React.FC = () => {
  console.log("DebugDemographics: Component is rendering");
  
  return (
    <div style={{ 
      minHeight: '100vh', 
      backgroundColor: '#f3f4f6', 
      padding: '24px',
      fontFamily: 'Arial, sans-serif'
    }}>
      <div style={{ 
        maxWidth: '1200px', 
        margin: '0 auto',
        backgroundColor: 'white',
        padding: '32px',
        borderRadius: '8px',
        boxShadow: '0 2px 4px rgba(0,0,0,0.1)'
      }}>
        <h1 style={{ 
          fontSize: '32px', 
          fontWeight: 'bold', 
          color: '#111827',
          marginBottom: '16px'
        }}>
          🎓 Debug Demographics Dashboard
        </h1>
        
        <p style={{ 
          color: '#6b7280', 
          fontSize: '16px',
          marginBottom: '24px'
        }}>
          If you can see this text, the basic React component is working!
        </p>

        <div style={{
          backgroundColor: '#dbeafe',
          border: '1px solid #3b82f6',
          borderRadius: '6px',
          padding: '16px',
          marginBottom: '24px'
        }}>
          <h3 style={{ color: '#1e40af', margin: '0 0 8px 0' }}>Component Status</h3>
          <p style={{ margin: 0, color: '#1e40af' }}>✅ React component rendered successfully</p>
        </div>

        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: '16px',
          marginBottom: '24px'
        }}>
          <div style={{
            backgroundColor: '#fef3c7',
            padding: '16px',
            borderRadius: '6px',
            border: '1px solid #f59e0b'
          }}>
            <h4 style={{ color: '#92400e', margin: '0 0 8px 0' }}>Test Card 1</h4>
            <p style={{ color: '#92400e', margin: 0, fontSize: '14px' }}>No external dependencies</p>
          </div>
          
          <div style={{
            backgroundColor: '#dcfce7',
            padding: '16px',
            borderRadius: '6px',
            border: '1px solid #10b981'
          }}>
            <h4 style={{ color: '#166534', margin: '0 0 8px 0' }}>Test Card 2</h4>
            <p style={{ color: '#166534', margin: 0, fontSize: '14px' }}>Pure inline styles</p>
          </div>
          
          <div style={{
            backgroundColor: '#ede9fe',
            padding: '16px',
            borderRadius: '6px',
            border: '1px solid #8b5cf6'
          }}>
            <h4 style={{ color: '#6b21a8', margin: '0 0 8px 0' }}>Test Card 3</h4>
            <p style={{ color: '#6b21a8', margin: 0, fontSize: '14px' }}>Basic functionality</p>
          </div>
        </div>

        <div style={{
          backgroundColor: '#fef2f2',
          border: '1px solid #ef4444',
          borderRadius: '6px',
          padding: '16px'
        }}>
          <h3 style={{ color: '#dc2626', margin: '0 0 8px 0' }}>Debugging Info</h3>
          <ul style={{ color: '#dc2626', margin: 0, paddingLeft: '20px' }}>
            <li>Component: DebugDemographics</li>
            <li>Styling: Inline styles (no Tailwind)</li>
            <li>Dependencies: None</li>
            <li>Check browser console for any errors</li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default DebugDemographics;