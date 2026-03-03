import { VersionHistoryCard } from './VersionHistoryCard';
import type { VersionHistoryItem } from '../model/types';

import './VersionHistoryList.css';

type Props = {
  items: VersionHistoryItem[];
  onView: (item: VersionHistoryItem) => void;
  onRestore: (item: VersionHistoryItem) => void;
};

export function VersionHistoryList({ items, onView, onRestore }: Props) {
  return (
    <ul className="sr-version-list">
      {items.map((item, index) => (
        <li key={item.id} className="sr-version-list__item">
          <VersionHistoryCard
            item={item}
            showAsCurrent={index === 0}
            onView={onView}
            onRestore={onRestore}
          />
        </li>
      ))}
    </ul>
  );
}
