import { analysisDomain } from './analysis';
import { authDomain } from './auth';
import { commonDomain } from './common';
import { profileDomain } from './profile';
import { resumeDomain } from './resume';
import { settingsDomain } from './settings';

const translation = {
  ...commonDomain,
  ...authDomain,
  ...profileDomain,
  ...settingsDomain,
  ...resumeDomain,
  ...analysisDomain,
} as const;

export const ptBR = { translation } as const;
