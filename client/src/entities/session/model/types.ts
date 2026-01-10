export type SessionUser = {
  id: string;
  email: string;
  full_name: string;
  email_verified: boolean;
  status?: string | null;
  created_at?: string | null;
  avatar_url?: string | null;
  // Backward-friendly alias (in case some endpoints return camelCase)
  avatarUrl?: string | null;
};

export type SessionStatus = 'unknown' | 'authenticated' | 'anonymous';


