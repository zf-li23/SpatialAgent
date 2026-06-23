/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        bio: {
          dark: '#0f172a',
          panel: '#1e293b',
          accent: '#06b6d4',
          accent2: '#10b981',
          text: '#e2e8f0',
          muted: '#64748b',
          border: '#334155',
        },
      },
    },
  },
  plugins: [],
}
