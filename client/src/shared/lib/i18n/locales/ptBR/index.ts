import { analysisDomain } from './analysis';
import { authDomain } from './auth';
import { commonDomain } from './common';
import { dashboardDomain } from './dashboard';
import { legalDomain } from './legal';
import { profileDomain } from './profile';
import { resumeDomain } from './resume';
import { settingsDomain } from './settings';
import { versionHistoryDomain } from './versionHistory';
import { notificationsDomain } from './notifications';
import { searchDomain } from './search';

const translation = {
  ...commonDomain,
  ...authDomain,
  ...legalDomain,
  ...profileDomain,
  ...settingsDomain,
  ...resumeDomain,
  ...analysisDomain,
  ...versionHistoryDomain,
  ...dashboardDomain,
  ...notificationsDomain,
  ...searchDomain,
} as const;

export const ptBR = { translation } as const;
