import { Outlet, useLocation } from 'react-router-dom';
import { Sidebar } from './Sidebar';

export function AppLayout() {
  const location = useLocation();
  const isLandingPage = location.pathname === '/';

  return (
    <div style={{ display: 'flex', minHeight: '100vh', background: '#f9fafb' }}>
      <Sidebar />
      <main style={{ flex: 1, marginLeft: '72px', overflow: 'auto', minHeight: '100vh' }}>
        {isLandingPage ? (
          <div style={{
            width: '100%', height: '100vh',
            background: 'linear-gradient(135deg, #1e3a5f 0%, #3B82F6 50%, #60a5fa 100%)',
            display: 'flex', alignItems: 'center', padding: '60px',
          }}>
            <div style={{ maxWidth: '500px' }}>
              <h1 style={{
                fontSize: '48px', fontWeight: 300, color: '#fff',
                margin: 0, letterSpacing: '4px', textTransform: 'uppercase', lineHeight: 1.2,
              }}>
                Invoice<br />Manager
              </h1>
              <div style={{ width: '60px', height: '3px', background: '#10B981', margin: '24px 0' }} />
              <p style={{
                fontSize: '16px', color: 'rgba(255,255,255,0.7)',
                margin: 0, letterSpacing: '1px',
              }}>
                Invoice Processing System
              </p>
            </div>
          </div>
        ) : (
          <Outlet />
        )}
      </main>
    </div>
  );
}
