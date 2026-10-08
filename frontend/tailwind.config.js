/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      fontFamily: {
        sans: ['system-ui', '-apple-system', 'Segoe UI', 'Roboto', 'Helvetica', 'Arial', 'sans-serif'],
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      colors: {
        bg: '#0F0F11',
        panel: '#161618',
        border: '#2C2C30',
        textMain: '#E4E4E5',
        textMuted: '#8B8D91',
        accentVer: '#238636', // green verified
        accentRev: '#D29922', // amber needs review
        accentFail: '#F85149', // red failed
      }
    },
  },
  plugins: [],
}
