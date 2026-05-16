/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        // Paleta Smurfit Westrock (azul corporativo)
        sw: {
          50:  '#eaf2ff',
          100: '#cfe0ff',
          200: '#9cc0ff',
          300: '#6a9eff',
          400: '#3a7bef',
          500: '#1a5dd9',
          600: '#0046b3',     // azul corporativo principal
          700: '#003a91',
          800: '#002d72',
          900: '#001f52',
        },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
