/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        canvas: '#FBFBFA',
        surface: '#FFFFFF',
        borderLight: '#EAEAEA',
        charcoal: '#111111',
        muted: '#787774',
        pastel: {
          red: '#FDEBEC',
          redText: '#9F2F2D',
          blue: '#E1F3FE',
          blueText: '#1F6C9F',
          green: '#EDF3EC',
          greenText: '#346538',
          yellow: '#FBF3DB',
          yellowText: '#956400',
          purple: '#F3EEFF',
          purpleText: '#69389F',
        }
      },
      fontFamily: {
        sans: ['"Inter"', 'system-ui', '-apple-system', 'BlinkMacSystemFont', '"Segoe UI"', 'Roboto', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"SF Mono"', 'Menlo', 'Consolas', 'monospace'],
      },
      boxShadow: {
        subtle: '0 1px 3px rgba(0,0,0,0.04), 0 1px 2px rgba(0,0,0,0.02)',
        float: '0 8px 30px rgba(0,0,0,0.08)',
      }
    },
  },
  plugins: [],
}
