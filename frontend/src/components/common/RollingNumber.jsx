import React, { useEffect, useState, useRef } from 'react';

export default function RollingNumber({ value = 0, duration = 850, prefix = '' }) {
  const [displayValue, setDisplayValue] = useState(0);
  const startValRef = useRef(0);
  const startTimeRef = useRef(null);
  const rafRef = useRef(null);

  useEffect(() => {
    const target = Math.round(value || 0);
    const start = startValRef.current;
    if (start === target) {
      setDisplayValue(target);
      return;
    }

    const animate = (timestamp) => {
      if (!startTimeRef.current) startTimeRef.current = timestamp;
      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);

      // Ease out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      const current = Math.round(start + (target - start) * easeOut);
      setDisplayValue(current);

      if (progress < 1) {
        rafRef.current = requestAnimationFrame(animate);
      } else {
        startValRef.current = target;
        startTimeRef.current = null;
      }
    };

    startTimeRef.current = null;
    rafRef.current = requestAnimationFrame(animate);

    return () => {
      if (rafRef.current) cancelAnimationFrame(rafRef.current);
    };
  }, [value, duration]);

  return (
    <span className="font-mono-tech tabular-nums">
      {prefix}{displayValue.toLocaleString('en-IN')}
    </span>
  );
}
