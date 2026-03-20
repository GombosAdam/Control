export type UserRole = 'admin' | 'accountant' | 'reviewer';

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: UserRole;
  is_active: boolean;
  last_login: string | null;
}

export interface TokenResponse {
  token: string;
  user: User;
}
