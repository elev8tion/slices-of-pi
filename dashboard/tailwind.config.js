/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        void: '#08080A',
        surface: {
          DEFAULT: 'rgba(255,255,255,0.03)',
          hover: 'rgba(255,255,255,0.05)',
          raised: 'rgba(255,255,255,0.06)',
        },
        border: {
          DEFAULT: 'rgba(255,255,255,0.05)',
          hover: 'rgba(255,255,255,0.08)',
          strong: 'rgba(255,255,255,0.12)',
        },
        accent: {
          DEFAULT: '#6366F1',
          hover: '#4F46E5',
          muted: 'rgba(99,102,241,0.12)',
          glow: 'rgba(99,102,241,0.25)',
        },
        text: {
          primary: '#F0F0F2',
          secondary: 'rgba(255,255,255,0.65)',
          tertiary: 'rgba(255,255,255,0.35)',
          muted: 'rgba(255,255,255,0.20)',
        },
        success: '#22C55E',
        warning: '#F59E0B',
        danger: '#EF4444',
      },
      fontFamily: {
        display: ['"Clash Display"', 'sans-serif'],
        body: ['Satoshi', 'sans-serif'],
        mono: ['"JetBrains Mono"', 'monospace'],
      },
      borderRadius: {
        card: '20px',
        btn: '12px',
        pill: '9999px',
      },
      backdropBlur: {
        glass: '32px',
      },
      animation: {
        'fade-up': 'fadeUp 0.7s cubic-bezier(0.32,0.72,0,1) forwards',
        'pulse-dot': 'pulseDot 2s ease-in-out infinite',
        'slide-up': 'slideUp 0.4s cubic-bezier(0.32,0.72,0,1)',
      },
      keyframes: {
        fadeUp: {
          from: { opacity: '0', transform: 'translateY(16px)' },
          to: { opacity: '1', transform: 'translateY(0)' },
        },
        pulseDot: {
          '0%, 100%': { boxShadow: '0 0 8px rgba(34,197,94,0.4)' },
          '50%': { boxShadow: '0 0 16px rgba(34,197,94,0.2)' },
        },
        slideUp: {
          from: { opacity: '0', transform: 'translateY(20px) scale(0.98)' },
          to: { opacity: '1', transform: 'translateY(0) scale(1)' },
        },
      },
    },
  },
  plugins: [],
}
