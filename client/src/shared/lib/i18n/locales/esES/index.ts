import { analysisDomain } from './analysis';
import { authDomain } from './auth';
import { commonDomain } from './common';
import { dashboardDomain } from './dashboard';
import { profileDomain } from './profile';
import { resumeDomain } from './resume';
import { settingsDomain } from './settings';
import { versionHistoryDomain } from './versionHistory';

const translation = {
  ...commonDomain,
  ...authDomain,
  ...profileDomain,
  ...settingsDomain,
  ...resumeDomain,
  ...analysisDomain,
  ...versionHistoryDomain,
  ...dashboardDomain,
} as const;

export const esES = { translation } as const;
