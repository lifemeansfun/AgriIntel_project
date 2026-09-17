import React from 'react';
import { useTheme } from '../../context/useTheme';

export default function GlassCard({ children, className = '', ...props }) {
  const { glassClass } = useTheme();

  return (
    <div className={`${glassClass} rounded-2xl ${className}`} {...props}>
      {children}
    </div>
  );
}
