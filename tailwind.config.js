/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        'templates/**/*.html'
    ],
    theme: {
        extend: {
            typography: {
                DEFAULT: {
                    css: {
                        a: {
                            color: '#fff',
                            '&:hover': {
                                color: 'rgb(45 212 191)',
                            },
                        },
                        ".codehilite": {
                            "border-radius": "0.25rem",
                        },
                    },
                },
            },
        },
    },
    daisyui: {
        themes: [
            "cupcake",
            "halloween",
        ],
    },
    plugins: [
        require('daisyui'),
        require('@tailwindcss/forms'),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
    ],
}
