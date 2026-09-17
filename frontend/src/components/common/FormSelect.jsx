import React from 'react';
import { useTheme } from '../../context/useTheme';

export default function FormSelect({
  id,
  label,
  icon: Icon,
  value,
  onChange,
  options = [],
  placeholder = 'Select option',
  disabled = false,
}) {
  const { textSecondary, inputClass } = useTheme();

  return (
    <div>
      <label htmlFor={id} className={`block text-sm font-medium mb-2 ${textSecondary} flex items-center gap-2`}>
        {Icon && <Icon className="w-4 h-4" />}
        <span>{label}</span>
      </label>
      <select
        id={id}
        value={value}
        onChange={onChange}
        disabled={disabled}
        className={`w-full border rounded-xl p-3 focus:outline-none focus:ring-2 transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed ${inputClass}`}
      >
        <option value="" disabled>{placeholder}</option>
        {options.map((opt) => {
          const val = typeof opt === 'object' ? opt.value : opt;
          const lbl = typeof opt === 'object' ? opt.label : opt;
          return (
            <option key={val} value={val}>
              {lbl}
            </option>
          );
        })}
      </select>
    </div>
  );
}
