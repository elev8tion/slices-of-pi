/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,ts,js}'],
  theme: {
    extend: {
      colors: {
        void: '#0A0A0A',
        surface: {
          DEFAULT: 'rgba(233,236,224,0.03)',
          hover: 'rgba(233,236,224,0.05)',
          raised: 'rgba(233,236,224,0.06)',
        },
        border: {
          DEFAULT: 'rgba(233,236,224,0.08)',
          hover: 'rgba(233,236,224,0.12)',
          strong: 'rgba(233,236,224,0.18)',
        },
        lime: {
          DEFAULT: '#9DD522',
          bright: '#D3ED2F',
          dark: '#699520',
        },
        olive: {
          dark: '#354A21',
          moss: '#4B5F2C',
          gray: '#5A6656',
        },
        teal: {
          gunmetal: '#364948',
        },
        accent: {
          DEFAULT: '#9DD522',
          hover: '#8BC01E',
          muted: 'rgba(157,213,34,0.12)',
          glow: 'rgba(157,213,34,0.25)',
        },
        text: {
          primary: '#E9ECE0',
          secondary: 'rgba(233,236,224,0.65)',
          tertiary: 'rgba(233,236,224,0.35)',
          muted: 'rgba(233,236,224,0.20)',
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
        sm: '4px',
        md: '8px',
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
