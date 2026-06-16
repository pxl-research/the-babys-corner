/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        // Matches thebabyscorner.be brand identity: softened pink-rose accent on warm cream.
        // Toned down from the vivid #E50051 so primary buttons read as friendly, not "danger".
        brand:        '#E86A8E', // signature rose — fills, accents, active states
        'brand-dark': '#C24E6E', // darker rose for text/links on light
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
