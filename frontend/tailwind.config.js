/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        cyber: {
          yellow: '#FCEE0A',
          red: '#E8213C',
          dark: '#1A0509',
          panel: '#3A0A12',
          white: '#FFFFFF'
        }
      },
      fontFamily: {
        sans: ['Rajdhani', 'sans-serif'],
        mono: ['Orbitron', 'monospace'],
      }
    },
  },
  plugins: [],
}
