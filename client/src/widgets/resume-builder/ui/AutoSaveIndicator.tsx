import { useEffect, useState } from 'react';

import './AutoSaveIndicator.css';

type Props = {
  lastSaved: Date | null;
  hasUnsavedChanges: boolean;
  onSave: () => void;
};

export function AutoSaveIndicator(props: Props) {
  const { lastSaved, hasUnsavedChanges, onSave } = props;
  const [timeAgo, setTimeAgo] = useState<string>('');

  useEffect(() => {
    if (!lastSaved) {
      setTimeAgo('');
      return;
    }

    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - lastSaved.getTime()) / 1000);
      if (seconds < 60) {
        setTimeAgo(`Salvo há ${seconds}s`);
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        setTimeAgo(`Salvo há ${minutes}min`);
      } else {
        const hours = Math.floor(seconds / 3600);
        setTimeAgo(`Salvo há ${hours}h`);
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 1000);
    return () => clearInterval(interval);
  }, [lastSaved]);

  if (!lastSaved && !hasUnsavedChanges) {
    return null;
  }

  return (
    <div className="sr-auto-save-indicator">
      {hasUnsavedChanges ? (
        <span className="sr-auto-save-indicator__unsaved">
          <i className="fa-solid fa-circle" aria-hidden />
          Alterações não salvas
        </span>
      ) : (
        <span className="sr-auto-save-indicator__saved">
          <i className="fa-solid fa-check-circle" aria-hidden />
          {timeAgo}
        </span>
      )}
    </div>
  );
}
