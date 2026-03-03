import { ACCENTS } from '@/shared/lib/theme/appearance';

const PUBLIC_PRIMARY = '#8b2e80';
const PUBLIC_SECONDARY = '#d62bc3';

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

function normalizeHex(value: string): string {
  const next = value.trim().replace(/^#/, '');
  if (/^[0-9a-fA-F]{6}$/.test(next)) return `#${next.toLowerCase()}`;
  if (/^[0-9a-fA-F]{3}$/.test(next)) {
    return `#${next
      .split('')
      .map((char) => `${char}${char}`)
      .join('')
      .toLowerCase()}`;
  }
  return '#c72cb8';
}

function mixHex(hex: string, factor: number): string {
  const normalized = normalizeHex(hex).slice(1);
  const amount = clamp(factor, -1, 1);
  const base = Number.parseInt(normalized, 16);
  const r = (base >> 16) & 255;
  const g = (base >> 8) & 255;
  const b = base & 255;
  const mix = (channel: number) => {
    const target = amount >= 0 ? 255 : 0;
    return Math.round(channel + (target - channel) * Math.abs(amount));
  };
  const rr = mix(r).toString(16).padStart(2, '0');
  const gg = mix(g).toString(16).padStart(2, '0');
  const bb = mix(b).toString(16).padStart(2, '0');
  return `#${rr}${gg}${bb}`;
}

export function getAccentHex(accentColor?: string | null): string {
  const fallback = '#c72cb8';
  if (!accentColor) return fallback;
  const accent = ACCENTS.find((item) => item.key === accentColor);
  return accent?.color ?? fallback;
}

function buildFaviconSvg(options: { primary: string; secondary: string; sparkle: string }) {
  const { primary, secondary, sparkle } = options;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" role="img" aria-label="Skill Refine"><defs><linearGradient id="sr-bg" x1="8" y1="8" x2="56" y2="56" gradientUnits="userSpaceOnUse"><stop offset="0%" stop-color="${primary}"/><stop offset="100%" stop-color="${secondary}"/></linearGradient></defs><rect x="4" y="4" width="56" height="56" rx="14" fill="url(#sr-bg)"/><path d="M20 14h18l8 8v28H20z" fill="#fff" fill-opacity=".95"/><path d="M38 14v10h10z" fill="${mixHex(secondary, 0.32)}"/><path d="M27 29h12a2 2 0 1 1 0 4H27a2 2 0 1 1 0-4Zm0 7h10a2 2 0 1 1 0 4H27a2 2 0 1 1 0-4Zm0 7h8a2 2 0 1 1 0 4h-8a2 2 0 1 1 0-4Z" fill="${mixHex(primary, -0.2)}"/><path d="m46.5 19.5 1.6 3.4 3.4 1.6-3.4 1.6-1.6 3.4-1.6-3.4-3.4-1.6 3.4-1.6z" fill="${sparkle}"/></svg>`;
}

function toDataUrl(svg: string): string {
  return `data:image/svg+xml,${encodeURIComponent(svg)}`;
}

function ensureFaviconLinks() {
  const head = document.head;
  const existing = head.querySelectorAll<HTMLLinkElement>('link[data-sr-favicon="true"]');
  if (existing.length >= 2) return Array.from(existing);

  const iconLink = document.createElement('link');
  iconLink.rel = 'icon';
  iconLink.type = 'image/svg+xml';
  iconLink.dataset.srFavicon = 'true';

  const shortcutIconLink = document.createElement('link');
  shortcutIconLink.rel = 'shortcut icon';
  shortcutIconLink.type = 'image/svg+xml';
  shortcutIconLink.dataset.srFavicon = 'true';

  head.append(iconLink, shortcutIconLink);
  return [iconLink, shortcutIconLink];
}

function removeDefaultReactFavicons() {
  const candidates = Array.from(document.querySelectorAll<HTMLLinkElement>('link[rel]'));
  for (const link of candidates) {
    const rel = link.rel.toLowerCase();
    const href = (link.getAttribute('href') ?? '').toLowerCase();
    const isFaviconRel = rel.includes('icon');
    const isReactDefault = href.includes('favicon.ico') || href.includes('logo192') || href.includes('logo512');
    if (isFaviconRel && isReactDefault) {
      link.remove();
    }
  }
}

export function applyContextFavicon(options: { isProtected: boolean; accentColor?: string | null }) {
  if (typeof document === 'undefined') return;

  removeDefaultReactFavicons();
  const links = ensureFaviconLinks();
  const accent = getAccentHex(options.accentColor);
  const primary = options.isProtected ? accent : PUBLIC_PRIMARY;
  const secondary = options.isProtected ? mixHex(accent, 0.22) : PUBLIC_SECONDARY;
  const sparkle = options.isProtected ? mixHex(accent, 0.5) : '#ffd8ff';
  const href = toDataUrl(buildFaviconSvg({ primary, secondary, sparkle }));

  for (const link of links) {
    if (link.getAttribute('href') !== href) {
      link.setAttribute('href', href);
    }
  }
}
