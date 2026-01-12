import type { CSSProperties } from 'react';

import './Skeleton.css';

type Props = {
  width?: number | string;
  height?: number | string;
  radius?: number;
  className?: string;
};

export function Skeleton(props: Props) {
  const { width = '100%', height = 14, radius = 12, className = '' } = props;
  const style: CSSProperties = { width, height, borderRadius: radius };
  return <div className={`sr-skeleton${className ? ` ${className}` : ''}`} style={style} />;
}
