import { useState } from 'react';
import { Leaf, Moon, Sun, Volume2, VolumeX } from '../common/Icons';
import { useTheme } from '../../context/useTheme';
import { toggleAmbientSoundscape, playTactileClick } from '../../utils/audio';

export default function Navbar({ formData = {} }) {
  const { darkMode, toggleDarkMode, glassClass, textPrimary, textSecondary } = useTheme();
  const [isAudioOn, setIsAudioOn] = useState(false);
  const handleAudio = () => { const next = !isAudioOn; setIsAudioOn(next); toggleAmbientSoundscape(next); };
  return <header className={`${glassClass} rounded-2xl px-4 sm:px-6 py-4 flex justify-between items-center gap-3 mb-7 ${textPrimary}`}><div className="flex gap-3 items-center"><Leaf className="w-6 h-6 text-emerald-600 dark:text-emerald-300" /><div><h1 className="text-2xl font-editorial font-bold">AgriIntel</h1><p className={`text-[10px] uppercase font-mono-tech tracking-wider ${textSecondary}`}>Regional crop advisory · course prototype</p></div></div><div className="flex gap-2 items-center"><span className={`hidden md:block text-xs mr-2 ${textSecondary}`}>{formData.district} · historical 2019</span><button type="button" onClick={handleAudio} aria-label={isAudioOn ? 'Mute ambient soundscape' : 'Enable ambient soundscape'} className="p-2 rounded-xl border border-emerald-500/20">{isAudioOn ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}</button><button type="button" onClick={() => { playTactileClick(); toggleDarkMode(); }} aria-label="Toggle day/night theme" className="rounded-xl border border-emerald-500/20 px-3 py-2 flex gap-2 items-center text-xs font-semibold">{darkMode ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}<span>{darkMode ? 'Night' : 'Day'}</span></button></div></header>;
}
