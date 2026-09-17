import React from 'react';

/**
 * Botanical ASCII Archetypes
 * Distinct agronomic species categories rendered as high-contrast stamp glyphs.
 */
const CEREAL_GLYPH = [' \\|/ ', '--o--', ' /|\\ '];
const LEGUME_GLYPH = [' .o. ', '( Y )', " 'o' "];
const OILSEED_GLYPH = [' *.* ', ':{+}:', " *'* "];

function getCropArchetype(cropName = '') {
  const name = cropName.toLowerCase();
  if (
    name.includes('gram') ||
    name.includes('tur') ||
    name.includes('arhar') ||
    name.includes('moong') ||
    name.includes('urad') ||
    name.includes('pulse') ||
    name.includes('lentil') ||
    name.includes('pea')
  ) {
    return LEGUME_GLYPH;
  }
  if (
    name.includes('cotton') ||
    name.includes('soy') ||
    name.includes('groundnut') ||
    name.includes('sugar') ||
    name.includes('mustard') ||
    name.includes('sunflower')
  ) {
    return OILSEED_GLYPH;
  }
  // Default to Cereal / Grain (Wheat, Rice, Maize, Bajra, Jowar, etc.)
  return CEREAL_GLYPH;
}

function AsciiCropGlyph({ cropName = '', className = '' }) {
  const glyph = getCropArchetype(cropName);

  return (
    <div
      className={`w-9 h-9 flex flex-col items-center justify-center rounded-lg border border-emerald-500/25 bg-emerald-500/10 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 font-mono text-[8.5px] leading-[1.1] select-none shrink-0 transition-transform duration-300 ease-out group-hover:scale-105 group-hover:rotate-1 ${className}`}
      title={`${cropName} (Botanical ASCII Stamp)`}
      aria-hidden="true"
    >
      <span className="whitespace-pre">{glyph[0]}</span>
      <span className="whitespace-pre font-bold">{glyph[1]}</span>
      <span className="whitespace-pre">{glyph[2]}</span>
    </div>
  );
}

export default React.memo(AsciiCropGlyph);
