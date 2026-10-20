/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: 'rgba(var(--color-ink), <alpha-value>)',
        paper: 'rgba(var(--color-paper), <alpha-value>)',
        sage: 'rgba(var(--color-sage), <alpha-value>)',
        moss: 'rgba(var(--color-moss), <alpha-value>)',
        amber: 'rgba(var(--color-amber), <alpha-value>)',
        navy: 'rgba(var(--color-navy), <alpha-value>)',
        'navy-light': 'rgba(var(--color-navy-light), <alpha-value>)',
        slate: {
          DEFAULT: '#607080',
          50: '#f8fafc',
          100: '#f1f5f9',
          200: '#e2e8f0',
          400: '#94a3b8',
          500: '#64748b',
          600: '#475569',
          700: '#334155',
          800: '#1e293b'
        }
      },
      boxShadow: {
        card: '0 18px 50px rgba(35, 55, 43, 0.10)'
      }
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
  ]
}
