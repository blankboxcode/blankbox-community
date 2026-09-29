'use client';

import { Check } from 'lucide-react';
import { physicalFormatGroups, physicalFormatLabel, type PhysicalFormat } from '@/lib/physical-media';

type Props = {
  value: PhysicalFormat[];
  onChange: (formats: PhysicalFormat[]) => void;
  compact?: boolean;
};

export function PhysicalFormatPicker({ value, onChange, compact = false }: Props) {
  const toggle = (format: PhysicalFormat) => {
    onChange(value.includes(format) ? value.filter((item) => item !== format) : [...value, format]);
  };

  return <div className={`physical-format-picker ${compact ? 'compact' : ''}`}>
    {physicalFormatGroups.map((group) => <section key={group.label}>
      <strong>{group.label}</strong>
      <div>{group.formats.map((format) => {
        const selected = value.includes(format);
        return <button type="button" key={format} className={selected ? 'selected' : ''} aria-pressed={selected} onClick={() => toggle(format)}>
          <span>{selected ? <Check size={13} /> : null}</span>{physicalFormatLabel(format)}
        </button>;
      })}</div>
    </section>)}
  </div>;
}
