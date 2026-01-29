import { useEffect, useState } from 'react';
import { useTranslation } from 'react-i18next';

import './AutoSaveIndicator.css';

type Props = {
  lastSaved: Date | null;
  hasUnsavedChanges: boolean;
  onSave: () => void;
};

export function AutoSaveIndicator(props: Props) {
  const { lastSaved, hasUnsavedChanges, onSave } = props;
  const { t } = useTranslation();
  const [timeAgo, setTimeAgo] = useState<string>('');

  useEffect(() => {
    if (!lastSaved) {
      setTimeAgo('');
      return;
    }

    const updateTimeAgo = () => {
      const seconds = Math.floor((Date.now() - lastSaved.getTime()) / 1000);
      if (seconds < 60) {
        setTimeAgo(t('resume.autoSaveAgo', { value: String(seconds), unit: t('resume.autoSaveSeconds') }));
      } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        setTimeAgo(t('resume.autoSaveAgo', { value: String(minutes), unit: t('resume.autoSaveMinutes') }));
      } else {
        const hours = Math.floor(seconds / 3600);
        setTimeAgo(t('resume.autoSaveAgo', { value: String(hours), unit: t('resume.autoSaveHours') }));
      }
    };

    updateTimeAgo();
    const interval = setInterval(updateTimeAgo, 1000);
    return () => clearInterval(interval);
  }, [lastSaved, t]);

  if (!lastSaved && !hasUnsavedChanges) {
    return null;
  }

  return (
    <div className="sr-auto-save-indicator">
      {hasUnsavedChanges ? (
        <span className="sr-auto-save-indicator__unsaved">
          <i className="fa-solid fa-circle" aria-hidden />
          {t('resume.autoSaveUnsaved')}
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
