import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { LogOut, RefreshCw } from 'lucide-react';
import { modules, servicePanels, type ModuleKey } from '../../config/modules';
import { useAuthStore } from '../../stores/authStore';
import { usePermissionStore } from '../../stores/permissionStore';
import { adminApi } from '../../services/api/admin';
import { authApi } from '../../services/api/auth';
import type { UserRole } from '../../types/user';

export function Sidebar() {
  const location = useLocation();
  const { t } = useTranslation();
  const { user, logout } = useAuthStore();
  const [showModules, setShowModules] = useState(false);

  const { hasAnyPermission, isLoaded: permsLoaded } = usePermissionStore();

  const visibleModules = Object.entries(modules).filter(([_, mod]) => {
    // Permission-based check (preferred)
    if (mod.permission && permsLoaded) {
      return hasAnyPermission(mod.permission);
    }
    // Fallback to role-based check
    return !mod.roles || mod.roles.includes(user?.role as UserRole);
  });

  const getCurrentModule = (): ModuleKey | null => {
    const path = location.pathname;
    if (path === '/') return null;
    // Find the module whose route is the longest match (most specific wins)
    let bestMatch: ModuleKey | null = null;
    let bestLen = 0;
    for (const [key, module] of visibleModules) {
      for (const route of module.routes) {
        if ((path === route || path.startsWith(route + '/')) && route.length > bestLen) {
          bestMatch = key as ModuleKey;
          bestLen = route.length;
        }
      }
    }
    return bestMatch;
  };

  const currentModuleKey = getCurrentModule();
  const currentModule = currentModuleKey ? modules[currentModuleKey] : null;

  useEffect(() => {
    if (location.pathname === '/' && !showModules) {
      setShowModules(true);
    }
  }, [location.pathname]);

  const isActiveRoute = (path: string) => location.pathname === path;

  const getInitials = (name: string) =>
    name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);

  return (
    <div style={{
      width: '72px', height: '100vh', background: '#1a1a1a',
      display: 'flex', flexDirection: 'column', position: 'fixed',
      left: 0, top: 0, zIndex: 100,
    }}>
      {/* Waffle - Module Launcher */}
      <button
        onClick={() => setShowModules(!showModules)}
        style={{
          width: '72px', height: '56px', background: 'transparent',
          border: 'none', cursor: 'pointer', display: 'flex',
          alignItems: 'center', justifyContent: 'center',
          borderBottom: '1px solid #333',
        }}
        title="App Launcher"
      >
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)',
          gap: '3px', width: '18px', height: '18px',
        }}>
          {[...Array(9)].map((_, i) => (
            <div key={i} style={{ background: '#fff', borderRadius: '1px', width: '100%', height: '100%' }} />
          ))}
        </div>
      </button>

      {/* Current Module Indicator */}
      {currentModule && (
        <>
          <div style={{
            padding: '12px 0', borderBottom: '1px solid #333',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px',
          }}>
            <div style={{
              width: '36px', height: '36px', borderRadius: '8px',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              color: '#fff', background: currentModule.color,
            }}>
              <currentModule.icon size={20} />
            </div>
            <span style={{
              fontSize: '9px', color: '#999', textTransform: 'uppercase',
              letterSpacing: '0.5px', textAlign: 'center', fontWeight: 500,
            }}>
              {t(currentModule.nameKey)}
            </span>
          </div>

          {/* Module Navigation */}
          <nav style={{ flex: 1, padding: '8px 0', display: 'flex', flexDirection: 'column', gap: '2px', overflowY: 'auto' }}>
            {currentModule.items.map((item) => {
              const active = isActiveRoute(item.path);
              return (
                <Link
                  key={item.path}
                  to={item.path}
                  style={{
                    display: 'flex', flexDirection: 'column', alignItems: 'center',
                    justifyContent: 'center', width: '72px', padding: '8px 4px',
                    textDecoration: 'none', borderLeft: `3px solid ${active ? currentModule.color : 'transparent'}`,
                    color: active ? '#fff' : '#666', background: active ? '#333' : 'transparent',
                    gap: '4px', transition: 'all 150ms ease',
                  }}
                >
                  <item.icon size={20} strokeWidth={active ? 2 : 1.5} />
                  <span style={{
                    fontSize: '9px', textAlign: 'center', lineHeight: 1.2,
                    maxWidth: '64px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {t(item.labelKey)}
                  </span>
                </Link>
              );
            })}
          </nav>
        </>
      )}

      {!currentModule && <div style={{ flex: 1 }} />}

      {/* User section with switcher */}
      <UserSwitcher user={user} logout={logout} getInitials={getInitials} t={t} />

      {/* Module Launcher Overlay — accordion panels */}
      {showModules && <LauncherOverlay
        visibleModules={visibleModules}
        onClose={() => setShowModules(false)}
        t={t}
      />}
    </div>
  );
}


function LauncherOverlay({
  visibleModules,
  onClose,
  t,
}: {
  visibleModules: [string, (typeof modules)[string]][];
  onClose: () => void;
  t: (key: string) => string;
}) {
  const visibleKeys = new Set(visibleModules.map(([k]) => k));

  return (
    <div
      style={{
        position: 'fixed', top: 0, left: '72px', right: 0, bottom: 0,
        background: 'rgba(15, 23, 42, 0.95)', zIndex: 200,
        backdropFilter: 'blur(8px)',
        display: 'flex', flexDirection: 'column',
        overflow: 'hidden',
      }}
      onClick={onClose}
    >
      <div
        style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          padding: '24px 40px', maxWidth: '1200px', width: '100%',
          margin: '0 auto', overflow: 'hidden',
        }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* Header — compact */}
        <div style={{ textAlign: 'center', marginBottom: '20px', flexShrink: 0 }}>
          <h2 style={{
            fontSize: '16px', fontWeight: 600, color: '#fff',
            margin: 0, letterSpacing: '1px', textTransform: 'uppercase',
          }}>
            Modulok
          </h2>
        </div>

        {/* All service panels in a flex column that fills remaining space */}
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column',
          gap: '16px', minHeight: 0,
        }}>
          {servicePanels.map((panel) => {
            const panelModules = Object.entries(modules)
              .filter(([k, mod]) => mod.service === panel.key && visibleKeys.has(k))
              .map(([k, mod]) => ({ key: k, mod }));

            if (panelModules.length === 0) return null;

            return (
              <div key={panel.key} style={{ flexShrink: 0 }}>
                {/* Panel label — single line */}
                <div style={{
                  display: 'flex', alignItems: 'center', gap: '8px',
                  marginBottom: '10px',
                }}>
                  <div style={{
                    width: '6px', height: '6px', borderRadius: '50%',
                    background: panel.color, flexShrink: 0,
                  }} />
                  <span style={{
                    fontSize: '11px', fontWeight: 700, color: panel.color,
                    letterSpacing: '0.5px', textTransform: 'uppercase',
                  }}>
                    {t(panel.labelKey)}
                  </span>
                  <div style={{ flex: 1, height: '1px', background: `${panel.color}22` }} />
                </div>

                {/* Module grid — horizontal, compact cards */}
                <div style={{
                  display: 'flex', flexWrap: 'wrap', gap: '8px',
                }}>
                  {panelModules.map(({ key, mod }) => (
                    <Link
                      key={key}
                      to={mod.items[0]?.path || '/'}
                      onClick={onClose}
                      style={{
                        display: 'flex', alignItems: 'center', gap: '10px',
                        padding: '10px 16px', borderRadius: '10px',
                        textDecoration: 'none', color: '#fff',
                        background: 'rgba(255,255,255,0.06)',
                        border: '1px solid rgba(255,255,255,0.08)',
                        transition: 'all 150ms ease',
                        cursor: 'pointer',
                        minWidth: '160px',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.12)';
                        e.currentTarget.style.borderColor = mod.color;
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.background = 'rgba(255,255,255,0.06)';
                        e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
                      }}
                    >
                      <div style={{
                        width: '36px', height: '36px', borderRadius: '10px',
                        background: mod.color, display: 'flex', alignItems: 'center',
                        justifyContent: 'center', color: '#fff', flexShrink: 0,
                        boxShadow: `0 2px 8px ${mod.color}44`,
                      }}>
                        <mod.icon size={18} strokeWidth={1.5} />
                      </div>
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 500, lineHeight: 1.2 }}>
                          {t(mod.nameKey)}
                        </div>
                        <div style={{ fontSize: '10px', color: 'rgba(255,255,255,0.35)', marginTop: '1px' }}>
                          {mod.items.length} elem
                        </div>
                      </div>
                    </Link>
                  ))}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}


function UserSwitcher({
  user,
  logout,
  getInitials,
  t,
}: {
  user: any;
  logout: () => void;
  getInitials: (name: string) => string;
  t: (key: string) => string;
}) {
  const [showPanel, setShowPanel] = useState(false);
  const [users, setUsers] = useState<any[]>([]);
  const [switching, setSwitching] = useState<string | null>(null);

  // Track if this session was started by an admin (survives user switches)
  const isAdmin = user?.role === 'admin';
  const hasAdminOrigin = isAdmin || !!sessionStorage.getItem('adminToken');

  const loadUsers = () => {
    if (hasAdminOrigin && users.length === 0) {
      // Use admin token for the user list request
      const adminToken = sessionStorage.getItem('adminToken');
      if (adminToken && !isAdmin) {
        // Temporarily use admin token to fetch users
        const origToken = sessionStorage.getItem('token');
        sessionStorage.setItem('token', adminToken);
        adminApi.listUsers({ limit: 200 })
          .then(data => setUsers(data.items || data))
          .catch(() => {})
          .finally(() => { if (origToken) sessionStorage.setItem('token', origToken); });
      } else {
        adminApi.listUsers({ limit: 200 }).then(data => setUsers(data.items || data)).catch(() => {});
      }
    }
  };

  const handleSwitch = async (targetId: string) => {
    if (targetId === user?.id) { setShowPanel(false); return; }
    setSwitching(targetId);
    try {
      // Save admin token on first switch
      if (isAdmin && !sessionStorage.getItem('adminToken')) {
        sessionStorage.setItem('adminToken', sessionStorage.getItem('token') || '');
        sessionStorage.setItem('adminUser', sessionStorage.getItem('currentUser') || '');
      }
      // Use admin token for the switch call
      const adminToken = sessionStorage.getItem('adminToken');
      const origToken = sessionStorage.getItem('token');
      if (adminToken) sessionStorage.setItem('token', adminToken);

      const response = await authApi.switchUser(targetId);

      sessionStorage.setItem('token', response.token);
      sessionStorage.setItem('currentUser', JSON.stringify(response.user));

      // If switching back to admin, clear the saved admin token
      if (response.user.role === 'admin') {
        sessionStorage.removeItem('adminToken');
        sessionStorage.removeItem('adminUser');
      }

      window.location.reload();
    } catch {
      setSwitching(null);
    }
  };

  const handleLogout = () => {
    sessionStorage.removeItem('adminToken');
    sessionStorage.removeItem('adminUser');
    logout();
  };

  const roleColors: Record<string, string> = {
    admin: '#EF4444',
    cfo: '#F59E0B',
    department_head: '#3B82F6',
    accountant: '#10B981',
    reviewer: '#8B5CF6',
    clerk: '#06B6D4',
  };

  return (
    <>
      <button
        onClick={() => { setShowPanel(!showPanel); loadUsers(); }}
        style={{
          padding: '12px 0', borderTop: '1px solid #333',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: '4px', background: 'transparent', border: 'none',
          cursor: 'pointer', width: '100%',
        }}
        title={hasAdminOrigin ? 'Felhasználó váltás' : t('auth.logout')}
      >
        <div style={{
          width: '36px', height: '36px', background: roleColors[user?.role] || '#3B82F6',
          borderRadius: '50%', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#fff', fontSize: '12px', fontWeight: 600,
        }}>
          {user ? getInitials(user.full_name) : 'U'}
        </div>
        <span style={{ fontSize: '8px', color: '#666', textAlign: 'center', maxWidth: '64px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {user?.full_name?.split(' ')[0] || 'User'}
        </span>
      </button>

      {/* User switcher popup */}
      {showPanel && (
        <div
          style={{
            position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
            background: 'rgba(0,0,0,0.3)', zIndex: 250,
          }}
          onClick={() => setShowPanel(false)}
        >
          <div
            style={{
              position: 'fixed', bottom: '16px', left: '80px',
              background: '#fff', borderRadius: '12px', padding: '8px',
              width: '280px', maxHeight: '70vh', overflowY: 'auto',
              boxShadow: '0 8px 32px rgba(0,0,0,0.2)',
            }}
            onClick={e => e.stopPropagation()}
          >
            {/* Current user */}
            <div style={{ padding: '10px 12px', borderBottom: '1px solid #e5e7eb', marginBottom: '4px' }}>
              <div style={{ fontSize: '13px', fontWeight: 600, color: '#1a1a1a' }}>{user?.full_name}</div>
              <div style={{ fontSize: '11px', color: '#888' }}>{user?.email} · {user?.role}</div>
            </div>

            {/* Impersonation banner */}
            {hasAdminOrigin && !isAdmin && (
              <div style={{ padding: '6px 12px', background: '#fef3c7', borderRadius: '6px', margin: '0 4px 4px', fontSize: '11px', color: '#92400e' }}>
                Admin módban vagy — {user?.full_name} nézetben
              </div>
            )}

            {/* User list */}
            {hasAdminOrigin && users.length > 0 && (
              <div style={{ marginBottom: '4px' }}>
                <div style={{ padding: '6px 12px', fontSize: '10px', fontWeight: 600, color: '#999', textTransform: 'uppercase' }}>
                  Váltás másik felhasználóra
                </div>
                {users.filter((u: any) => u.is_active).map((u: any) => (
                  <button
                    key={u.id}
                    onClick={() => handleSwitch(u.id)}
                    disabled={switching !== null}
                    style={{
                      width: '100%', display: 'flex', alignItems: 'center', gap: '10px',
                      padding: '8px 12px', border: 'none', borderRadius: '6px',
                      background: u.id === user?.id ? '#eff6ff' : 'transparent',
                      cursor: switching ? 'wait' : 'pointer', textAlign: 'left',
                      opacity: switching && switching !== u.id ? 0.5 : 1,
                    }}
                    onMouseEnter={e => { if (u.id !== user?.id) e.currentTarget.style.background = '#f3f4f6'; }}
                    onMouseLeave={e => { if (u.id !== user?.id) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <div style={{
                      width: '28px', height: '28px', borderRadius: '50%',
                      background: roleColors[u.role] || '#6B7280',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: '#fff', fontSize: '10px', fontWeight: 600, flexShrink: 0,
                    }}>
                      {getInitials(u.full_name)}
                    </div>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontSize: '12px', fontWeight: 500, color: '#333' }}>
                        {u.full_name}
                        {u.id === user?.id && <span style={{ color: '#3B82F6', marginLeft: '4px' }}>●</span>}
                      </div>
                      <div style={{ fontSize: '10px', color: '#999' }}>{u.role}</div>
                    </div>
                    {switching === u.id && (
                      <RefreshCw size={14} style={{ color: '#888', animation: 'spin 0.8s linear infinite' }} />
                    )}
                  </button>
                ))}
              </div>
            )}

            {/* Logout */}
            <button
              onClick={handleLogout}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: '8px',
                padding: '10px 12px', border: 'none', borderRadius: '6px',
                background: 'transparent', cursor: 'pointer', borderTop: '1px solid #e5e7eb',
                color: '#EF4444', fontSize: '12px', fontWeight: 500,
              }}
              onMouseEnter={e => { e.currentTarget.style.background = '#fef2f2'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <LogOut size={14} /> {t('auth.logout')}
            </button>
          </div>
        </div>
      )}

      <style>{`@keyframes spin { to { transform: rotate(360deg); } }`}</style>
    </>
  );
}
