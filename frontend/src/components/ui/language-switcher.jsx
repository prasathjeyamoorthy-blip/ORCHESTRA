import React from 'react'
import { cn } from '@/lib/utils'

const LANGUAGES = [
  { code: 'en', label: 'EN', full: 'English' },
  { code: 'ta', label: 'தமிழ்', full: 'Tamil' },
]

export function LanguageSwitcher({ value, onChange }) {
  return (
    <div className="flex items-center gap-0.5 rounded-lg border border-white/[0.08] bg-white/[0.03] p-0.5">
      {LANGUAGES.map(lang => (
        <button
          key={lang.code}
          onClick={() => onChange(lang.code)}
          title={lang.full}
          className={cn(
            'px-2.5 py-1 rounded-md text-xs font-medium transition-all',
            value === lang.code
              ? 'bg-purple-600 text-white shadow-sm'
              : 'text-white/40 hover:text-white/70 hover:bg-white/[0.05]'
          )}
        >
          {lang.label}
        </button>
      ))}
    </div>
  )
}
