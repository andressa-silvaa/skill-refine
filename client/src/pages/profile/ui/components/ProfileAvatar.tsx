import { useEffect, useState } from 'react';

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
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    setFailed(false);
  }, [src]);

  return (
    <div className="sr-profile-avatar" aria-label="Foto de perfil">
      {src && !failed ? (
        <img className="sr-profile-avatar__img" src={src} alt="" onError={() => setFailed(true)} />
      ) : (
        <span className="sr-profile-avatar__txt">{initials}</span>
      )}
    </div>
  );
}


