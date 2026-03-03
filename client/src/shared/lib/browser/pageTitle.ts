import { matchPath } from 'react-router-dom';

type Translate = (key: string) => string;

type TitleResolver = {
  match: (pathname: string) => boolean;
  title: string | ((t: Translate) => string);
};

const PUBLIC_TITLE_RULES: TitleResolver[] = [
  { match: (pathname) => Boolean(matchPath('/login', pathname)), title: 'Login' },
  { match: (pathname) => Boolean(matchPath('/register', pathname)), title: 'Register' },
  { match: (pathname) => Boolean(matchPath('/confirm-email', pathname)), title: 'Confirm Email' },
  { match: (pathname) => Boolean(matchPath('/verify-email', pathname)), title: 'Verify Email' },
  { match: (pathname) => Boolean(matchPath('/oauth/callback', pathname)), title: 'OAuth Callback' },
  { match: (pathname) => Boolean(matchPath('/reset/email', pathname)), title: 'Reset Password' },
  { match: (pathname) => Boolean(matchPath('/reset/code', pathname)), title: 'Reset Password' },
  { match: (pathname) => Boolean(matchPath('/reset/new', pathname)), title: 'Reset Password' },
  { match: (pathname) => Boolean(matchPath('/reset/success', pathname)), title: 'Password Reset' },
  { match: (pathname) => Boolean(matchPath('/resume/print/:resumeId', pathname)), title: 'Resume Print' },
];

const PROTECTED_TITLE_RULES: TitleResolver[] = [
  { match: (pathname) => Boolean(matchPath('/protected/resumes', pathname)), title: (t) => t('resume.title') },
  { match: (pathname) => Boolean(matchPath('/protected/profile', pathname)), title: (t) => t('profile.title') },
  { match: (pathname) => Boolean(matchPath('/protected/settings', pathname)), title: (t) => t('settings.title') },
  { match: (pathname) => Boolean(matchPath('/protected/ai-analysis', pathname)), title: (t) => t('analysis.title') },
  {
    match: (pathname) => Boolean(matchPath('/protected/version-history', pathname)),
    title: (t) => t('versionHistory.title'),
  },
  { match: (pathname) => Boolean(matchPath('/protected', pathname)), title: (t) => t('resume.title') },
];

function resolveTitleFromRules(pathname: string, rules: TitleResolver[], t: Translate) {
  const rule = rules.find((item) => item.match(pathname));
  if (!rule) return null;
  return typeof rule.title === 'string' ? rule.title : rule.title(t);
}

export function isProtectedPath(pathname: string): boolean {
  return Boolean(matchPath('/protected/*', pathname) || matchPath('/protected', pathname));
}

export function resolvePageTitle(pathname: string, t: Translate): string {
  const isProtected = isProtectedPath(pathname);
  const fromProtected = isProtected ? resolveTitleFromRules(pathname, PROTECTED_TITLE_RULES, t) : null;
  const fromPublic = !isProtected ? resolveTitleFromRules(pathname, PUBLIC_TITLE_RULES, t) : null;
  const pageTitle = fromProtected ?? fromPublic ?? 'Skill Refine';
  return pageTitle === 'Skill Refine' ? pageTitle : `${pageTitle} | Skill Refine`;
}
