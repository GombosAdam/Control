import { Link, useLocation } from 'react-router-dom';
import { useState, useEffect } from 'react';
import { useTranslation } from 'react-i18next';
import { LogOut } from 'lucide-react';
import { modules, servicePanels, type ModuleKey } from '../../config/modules';
import { useAuthStore } from '../../stores/authStore';
import type { UserRole } from '../../types/user';

export function Sidebar() {
  const location = useLocation();
  const { t } = useTranslation();
  const { user, logout } = useAuthStore();
  const [showModules, setShowModules] = useState(false);

  const visibleModules = Object.entries(modules).filter(([_, mod]) =>
    !mod.roles || mod.roles.includes(user?.role as UserRole)
  );

  const getCurrentModule = (): ModuleKey | null => {
    const path = location.pathname;
    if (path === '/') return null;
    for (const [key, module] of visibleModules) {
      if (module.routes.some(route => path.startsWith(route))) {
        return key as ModuleKey;
      }
    }
    return null;
  };

  const currentModuleKey = getCurrentModule();
  const currentModule = currentModuleKey ? modules[currentModuleKey] : null;

  useEffect(() => {
    if (location.pathname === '/' && !showModules) {
      setShowModules(true);
    }
  }, [location.pathname]);

  const isActiveRoute = (path: string) => location.pathname === path || location.pathname.startsWith(path + '/');

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

      {/* User section */}
      <button
        onClick={logout}
        style={{
          padding: '12px 0', borderTop: '1px solid #333',
          display: 'flex', flexDirection: 'column', alignItems: 'center',
          gap: '4px', background: 'transparent', border: 'none',
          cursor: 'pointer', width: '100%',
        }}
        title={t('auth.logout')}
      >
        <div style={{
          width: '36px', height: '36px', background: '#3B82F6',
          borderRadius: '50%', display: 'flex', alignItems: 'center',
          justifyContent: 'center', color: '#fff', fontSize: '12px', fontWeight: 600,
        }}>
          {user ? getInitials(user.full_name) : 'U'}
        </div>
        <span style={{ fontSize: '8px', color: '#666', textAlign: 'center' }}>
          {user?.full_name?.split(' ')[0] || 'User'}
        </span>
      </button>

      {/* Module Launcher Overlay — 3 service panels */}
      {showModules && (() => {
        const visibleKeys = new Set(visibleModules.map(([k]) => k));

        return (
          <div
            style={{
              position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
              background: 'rgba(0,0,0,0.5)', zIndex: 200,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
            onClick={() => setShowModules(false)}
          >
            <div
              style={{
                background: '#fff', borderRadius: '16px', padding: '24px',
                maxWidth: '820px', width: '100%',
                display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px',
              }}
              onClick={(e) => e.stopPropagation()}
            >
              {servicePanels.map((panel) => {
                const panelModules = Object.entries(modules)
                  .filter(([k, mod]) => mod.service === panel.key && visibleKeys.has(k))
                  .map(([k, mod]) => ({ key: k, mod }));

                if (panelModules.length === 0) return null;

                return (
                  <div
                    key={panel.key}
                    style={{
                      background: '#fafafa', borderRadius: '12px', padding: '20px 16px',
                      borderTop: `3px solid ${panel.color}`,
                    }}
                  >
                    <div style={{
                      fontSize: '13px', fontWeight: 700, color: panel.color,
                      marginBottom: '4px',
                    }}>
                      {t(panel.labelKey)}
                    </div>
                    <div style={{
                      fontSize: '10px', color: '#999', marginBottom: '16px', lineHeight: 1.4,
                    }}>
                      {t(panel.description)}
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {panelModules.map(({ key, mod }) => (
                        <Link
                          key={key}
                          to={mod.items[0]?.path || '/'}
                          onClick={() => setShowModules(false)}
                          style={{
                            display: 'flex', alignItems: 'center', gap: '10px',
                            padding: '8px 10px', borderRadius: '8px',
                            textDecoration: 'none', color: '#333', transition: 'all 150ms',
                          }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = '#f0f0f0')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                        >
                          <div style={{
                            width: '36px', height: '36px', borderRadius: '8px',
                            background: mod.color, display: 'flex', alignItems: 'center',
                            justifyContent: 'center', color: '#fff', flexShrink: 0,
                          }}>
                            <mod.icon size={18} />
                          </div>
                          <span style={{ fontSize: '12px', fontWeight: 500 }}>
                            {t(mod.nameKey)}
                          </span>
                        </Link>
                      ))}
                    </div>
                  </div>
                );
              })}
            </div>
          </div>
        );
      })()}
    </div>
  );
}
