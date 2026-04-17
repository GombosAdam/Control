import { Navigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/authStore';
import { usePermissionStore } from '../../stores/permissionStore';
import { modules } from '../../config/modules';
import type { UserRole } from '../../types/user';

function getFirstAllowedPath(role: UserRole, hasAnyPermission: (p: string) => boolean, permsLoaded: boolean): string {
  for (const mod of Object.values(modules)) {
    const allowed = mod.permission && permsLoaded
      ? hasAnyPermission(mod.permission)
      : !mod.roles || mod.roles.includes(role);
    if (allowed && mod.items.length > 0) {
      return mod.items[0].path;
    }
  }
  return '/';
}

export function PermissionGuard({
  resource,
  action = 'read',
  children,
}: {
  resource: string;
  action?: string;
  children: React.ReactNode;
}) {
  const { user } = useAuthStore();
  const { hasPermission, hasAnyPermission, isLoaded } = usePermissionStore();

  // Don't block while permissions are loading
  if (!isLoaded) return null;

  if (!hasPermission(resource, action)) {
    const fallback = user
      ? getFirstAllowedPath(user.role, hasAnyPermission, isLoaded)
      : '/';
    return <Navigate to={fallback} replace />;
  }
  return <>{children}</>;
}
