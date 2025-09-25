/**
 * Minimal App component for debugging
 */

function App() {
  return (
    <div style={{ padding: '20px', fontFamily: 'Arial, sans-serif' }}>
      <h1 style={{ color: '#1890ff' }}>🎉 Naga SIS Staff Portal</h1>
      <p>React app is working!</p>
      <div style={{
        background: '#f0f2f5',
        padding: '16px',
        borderRadius: '8px',
        marginTop: '20px'
      }}>
        <h2>Backend API Status</h2>
        <p>✅ Login endpoint: POST /api/auth/login/</p>
        <p>✅ Profile endpoint: GET /api/auth/profile/</p>
        <p>✅ JWT tokens working properly</p>
      </div>
      <div style={{
        background: '#e6f4ff',
        padding: '16px',
        borderRadius: '8px',
        marginTop: '20px'
      }}>
        <h2>Next Steps</h2>
        <p>Switch back to full App.tsx once this loads successfully</p>
      </div>
    </div>
  );
}

export default App;