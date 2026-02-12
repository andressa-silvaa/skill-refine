export {};
function flattenLeafKeys(obj: unknown, prefix = ''): string[] {
  if (obj === null || obj === undefined) return [];
  if (typeof obj === 'string') return prefix ? [prefix] : [];
  if (typeof obj !== 'object') return [];
  const acc: string[] = [];
  for (const [k, v] of Object.entries(obj)) {
    const path = prefix ? `${prefix}.${k}` : k;
    if (typeof v === 'string') acc.push(path);
    else if (v !== null && typeof v === 'object' && !Array.isArray(v)) acc.push(...flattenLeafKeys(v, path));
  }
  return acc;
}

function getValueAt(obj: Record<string, unknown>, path: string): unknown {
  const parts = path.split('.');
  let cur: unknown = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== 'object') return undefined;
    cur = (cur as Record<string, unknown>)[p];
  }
  return cur;
}

function main(): void {
  const ptBR = require('../locales/ptBR').ptBR as { translation: Record<string, unknown> };
  const enUS = require('../locales/enUS').enUS as { translation: Record<string, unknown> };
  const esES = require('../locales/esES').esES as { translation: Record<string, unknown> };

  const locales = {
    'pt-BR': ptBR.translation,
    'en-US': enUS.translation,
    'es-ES': esES.translation,
  };
  const allKeys = new Set<string>();
  const keysByLocale: Record<string, Set<string>> = {};
  for (const [name, translation] of Object.entries(locales)) {
    const keys = new Set(flattenLeafKeys(translation));
    keys.forEach((k) => allKeys.add(k));
    keysByLocale[name] = keys;
  }

  let failed = false;

  for (const key of allKeys) {
    for (const [name, keys] of Object.entries(keysByLocale)) {
      if (!keys.has(key)) {
        console.error(`[i18n:check] Missing key in ${name}: ${key}`);
        failed = true;
      }
    }
  }

  for (const [name, keys] of Object.entries(keysByLocale)) {
    for (const key of keys) {
      if (!allKeys.has(key)) {
        console.error(`[i18n:check] Extra key in ${name} (not in all locales): ${key}`);
        failed = true;
      }
    }
  }

  for (const key of allKeys) {
    for (const [name, translation] of Object.entries(locales)) {
      const val = getValueAt(translation as Record<string, unknown>, key);
      if (val === undefined) {
        console.error(`[i18n:check] Undefined value in ${name} at key: ${key}`);
        failed = true;
      } else if (typeof val === 'object' && val !== null && !Array.isArray(val) && Object.keys(val).length === 0) {
        console.error(`[i18n:check] Empty object in ${name} at key: ${key}`);
        failed = true;
      }
    }
  }

  if (failed) process.exit(1);
  console.log('[i18n:check] OK: pt-BR, en-US, es-ES keys are consistent.');
}

main();

export {};
