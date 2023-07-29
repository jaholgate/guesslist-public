/** @type {import('tailwindcss').Config} */
module.exports = {
	content: ['./guesslist/templates/*.html', './guesslist/templates/**/*.html'],
	theme: {
		extend: {
			// fontFamily: {
			// 	sans: ['Rubik', defaultTheme.fontFamily.sans],
			// },
		},
	},
	plugins: [require('@tailwindcss/forms')],
};
