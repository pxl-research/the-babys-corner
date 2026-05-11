/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        brand:  '#8B9E77',
        cream:  '#FAF7F2',
        ink:    '#2C2C2C',
        danger: '#C0392B',
        muted:  '#D6D0C8',
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
