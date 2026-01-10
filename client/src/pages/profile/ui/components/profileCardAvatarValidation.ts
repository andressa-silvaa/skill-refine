const MAX_AVATAR_BYTES = 2 * 1024 * 1024;
const ALLOWED_TYPES = new Set(['image/jpeg', 'image/png', 'image/webp']);

export function validateAvatarFile(file: File): string | null {
  if (!ALLOWED_TYPES.has(file.type)) return 'Formato inválido. Envie JPG, PNG ou WEBP.';
  if (file.size > MAX_AVATAR_BYTES) return 'Arquivo muito grande. Tamanho máximo: 2MB.';
  return null;
}
