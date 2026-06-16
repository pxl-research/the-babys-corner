/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand:        '#8B9E77', // sage green — fills, accents, active states
        'brand-dark': '#5C6E50', // dark sage for text/links on light (WCAG AA)
        cream:        '#FAF7F2', // warm off-white page background
        ink:          '#2C2C2C', // near-black body text
        danger:       '#C0392B',
        muted:        '#D6D0C8',
      },
      fontFamily: {
        sans:    ['Inter', 'sans-serif'],
        display: ['Playfair Display', 'serif'],
      },
      borderRadius: {
        btn:  '10px',
        card: '16px',
      },
    },
  },
  plugins: [],
}
