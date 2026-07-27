/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{vue,js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        ink: '#17231d',
        paper: '#f5f3ec',
        sage: '#5c755f',
        moss: '#2f4a38',
        amber: '#d69b45',
        navy: '#14283d',
        'navy-light': '#1e3a55',
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
  plugins: []
}
