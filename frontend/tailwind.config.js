/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Matches thebabyscorner.be brand identity: vivid pink accent on warm cream.
        brand:        '#E50051', // signature pink — fills, accents, active states
        'brand-dark': '#B2003F', // darker pink for text/links on light (site link color)
        cream:        '#FFF9F0', // warm off-white page background
        ink:          '#403F3D', // warm charcoal body text
        danger:       '#C0392B',
        muted:        '#D6D0C8',
      },
      fontFamily: {
        sans:    ['Mulish', 'sans-serif'],
        display: ['Quicksand', 'sans-serif'],
      },
      borderRadius: {
        btn:  '12px',
        card: '16px',
      },
    },
  },
  plugins: [],
}
