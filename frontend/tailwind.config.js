/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  darkMode: 'class',
  theme: {
    extend: {
      colors: {
        /* ── Surface / Background tokens ── */
        surface: {
          DEFAULT: 'var(--surface)',
          50: 'var(--surface-50)',
          100: 'var(--surface-100)',
          raised: 'var(--surface-raised)',
          overlay: 'var(--surface-overlay)',
          sunken: 'var(--surface-sunken)',
        },
        border: {
          DEFAULT: 'var(--border)',
          light: 'var(--border-light)',
          strong: 'var(--border-strong)',
        },
        /* ── Text tokens ── */
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'text-inverse': 'var(--text-inverse)',
        /* ── Accent: Calm indigo-blue ── */
        accent: {
          DEFAULT: 'var(--accent)',
          light: 'var(--accent-light)',
          dark: 'var(--accent-dark)',
          subtle: 'var(--accent-subtle)',
          muted: 'var(--accent-muted)',
        },
        /* ── Status ── */
        'status-success': '#16a34a',
        'status-warning': '#d97706',
        'status-error': '#dc2626',

        /* ── Legacy aliases (backward compat) ── */
        dark: {
          DEFAULT: 'var(--surface)',
          50: 'var(--surface-sunken)',
          100: 'var(--surface-raised)',
          200: 'var(--surface-overlay)',
          300: 'var(--surface-overlay)',
          400: 'var(--surface-overlay)',
        },
      },
      fontFamily: {
        sans: ['"Google Sans"', 'Inter', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      fontSize: {
        '2xs': ['0.6875rem', { lineHeight: '1rem' }],
        'xs': ['0.75rem', { lineHeight: '1.125rem' }],
        'sm': ['0.8125rem', { lineHeight: '1.25rem' }],
        'base': ['0.875rem', { lineHeight: '1.375rem' }],
        'md': ['0.9375rem', { lineHeight: '1.5rem' }],
        'lg': ['1.0625rem', { lineHeight: '1.625rem' }],
        'xl': ['1.25rem', { lineHeight: '1.75rem' }],
        '2xl': ['1.5rem', { lineHeight: '2rem' }],
        '3xl': ['1.875rem', { lineHeight: '2.25rem' }],
        '4xl': ['2.25rem', { lineHeight: '2.625rem' }],
      },
      borderRadius: {
        'sm': '0.375rem',
        'md': '0.5rem',
        'lg': '0.625rem',
        'xl': '0.75rem',
        '2xl': '1rem',
        '3xl': '1.25rem',
      },
      boxShadow: {
        'xs': '0 1px 2px 0 rgba(0,0,0,0.03)',
        'sm': '0 1px 3px 0 rgba(0,0,0,0.06), 0 1px 2px -1px rgba(0,0,0,0.06)',
        'md': '0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05)',
        'lg': '0 10px 15px -3px rgba(0,0,0,0.08), 0 4px 6px -4px rgba(0,0,0,0.05)',
        'panel': '0 1px 3px rgba(0,0,0,0.04), 0 0 0 1px var(--border)',
        'elevated': '0 8px 24px rgba(0,0,0,0.12), 0 0 0 1px var(--border-light)',
        'glow': '0 0 20px var(--accent-muted)',
        'glow-sm': '0 0 10px var(--accent-muted)',
        /* Legacy */
        'glass': '0 4px 24px rgba(0,0,0,0.12), 0 0 0 1px var(--border-light)',
        'glass-sm': '0 2px 12px rgba(0,0,0,0.08), 0 0 0 1px var(--border-light)',
      },
      spacing: {
        '4.5': '1.125rem',
        '13': '3.25rem',
        '15': '3.75rem',
        '18': '4.5rem',
      },
      animation: {
        'fade-in': 'fadeIn 0.2s ease-out',
        'fade-out': 'fadeOut 0.2s ease-in forwards',
        'fade-up': 'fadeUp 0.25s ease-out',
        'scale-in': 'scaleIn 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
        'scale-out': 'scaleOut 0.15s ease-in forwards',
        'slide-in-right': 'slideInRight 0.25s ease-out',
        'slide-in-left': 'slideInLeft 0.25s ease-out',
        'shimmer': 'shimmer 2s ease-in-out infinite',
        'pulse-subtle': 'pulseSubtle 2s ease-in-out infinite',
        'spin-slow': 'spin 3s linear infinite',
        'progress': 'progress 2s ease-in-out infinite',
      },
      keyframes: {
        fadeIn: {
          '0%': { opacity: '0' },
          '100%': { opacity: '1' },
        },
        fadeOut: {
          '0%': { opacity: '1' },
          '100%': { opacity: '0' },
        },
        fadeUp: {
          '0%': { opacity: '0', transform: 'translateY(6px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        scaleIn: {
          '0%': { opacity: '0', transform: 'scale(0.97)' },
          '100%': { opacity: '1', transform: 'scale(1)' },
        },
        scaleOut: {
          '0%': { opacity: '1', transform: 'scale(1)' },
          '100%': { opacity: '0', transform: 'scale(0.97)' },
        },
        slideInRight: {
          '0%': { opacity: '0', transform: 'translateX(8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        slideInLeft: {
          '0%': { opacity: '0', transform: 'translateX(-8px)' },
          '100%': { opacity: '1', transform: 'translateX(0)' },
        },
        shimmer: {
          '0%': { backgroundPosition: '-200% 0' },
          '100%': { backgroundPosition: '200% 0' },
        },
        pulseSubtle: {
          '0%, 100%': { opacity: '0.4' },
          '50%': { opacity: '1' },
        },
        progress: {
          '0%': { transform: 'translateX(-100%)' },
          '50%': { transform: 'translateX(100%)' },
          '100%': { transform: 'translateX(-100%)' },
        },
      },
      transitionTimingFunction: {
        'smooth': 'cubic-bezier(0.16, 1, 0.3, 1)',
      },
    },
  },
  plugins: [],
}
