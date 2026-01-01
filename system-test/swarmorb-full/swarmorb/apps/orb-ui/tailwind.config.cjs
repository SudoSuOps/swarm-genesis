/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
  theme: {
    extend: {
      colors: {
        surface: {
          950: '#050506',
          900: '#0a0a0c',
          800: '#111114',
          700: '#1a1a1f',
          600: '#27272e',
          500: '#3f3f48',
        },
        accent: {
          DEFAULT: '#22d3ee',
          muted: '#0891b2',
          dim: '#164e63',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
