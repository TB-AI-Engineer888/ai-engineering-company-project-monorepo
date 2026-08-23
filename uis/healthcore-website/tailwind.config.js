/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./*.html", "./*.js"],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#EAF4F4', 100: '#D2E7E8', 200: '#A6CFD1', 400: '#1E8A90',
          500: '#136E73', 600: '#0B5D63', 700: '#094A4F', 800: '#073A3E', 900: '#052E31'
        },
        accent: {
          50: '#FDEEE5', 100: '#FBDCC9', 400: '#F2985E', 500: '#EF7B45',
          600: '#DB6530', 700: '#B84F22', 800: '#8F3D1C'
        }
      },
      fontFamily: {
        display: ['"Fraunces"', 'serif'],
        sans: ['"Inter"', 'sans-serif']
      }
    }
  },
  plugins: [require('@tailwindcss/forms')]
};