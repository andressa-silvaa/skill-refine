import './ProfileAvatar.css';

type Props = {
  fullName: string;
  src?: string | null;
};

function initialsFromName(fullName: string) {
  const parts = fullName
    .trim()
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2);
  const initials = parts.map((p) => p[0]?.toUpperCase() ?? '').join('');
  return initials || 'U';
}

export function ProfileAvatar(props: Props) {
  const { fullName, src } = props;
  const initials = initialsFromName(fullName);

  return (
    <div className="sr-profile-avatar" aria-label="Foto de perfil">
      {src ? <img className="sr-profile-avatar__img" src={src} alt="" /> : <span className="sr-profile-avatar__txt">{initials}</span>}
    </div>
  );
}


