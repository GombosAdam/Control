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

export function RoleGuard({ roles, children }: { roles: UserRole[]; children: React.ReactNode }) {
  const { user } = useAuthStore();
  const { hasAnyPermission, isLoaded: permsLoaded } = usePermissionStore();

  if (!user || !roles.includes(user.role)) {
    const fallback = user
      ? getFirstAllowedPath(user.role, hasAnyPermission, permsLoaded)
      : '/';
    return <Navigate to={fallback} replace />;
  }
  return <>{children}</>;
}
