export type UserRole = 'admin' | 'cfo' | 'department_head' | 'accountant' | 'reviewer' | 'clerk';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department_id: string | null;
  is_active: boolean;
  last_login: string | null;
}

export interface TokenResponse {
  token: string;
  user: User;
}
