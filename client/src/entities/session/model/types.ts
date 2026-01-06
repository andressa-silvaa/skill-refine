export type SessionUser = {
  id: string;
  email: string;
  full_name: string;
  email_verified: boolean;
};

export type SessionStatus = 'unknown' | 'authenticated' | 'anonymous';


