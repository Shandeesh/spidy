/** @type {import('tailwindcss').Config} */
module.exports = {
    content: [
        "./pages/**/*.{js,ts,jsx,tsx}",
        "./components/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                spidy: {
                    dark: 'var(--bg-primary)',
                    card: 'var(--bg-card)',
                    primary: 'var(--color-primary)',
                    accent: 'var(--color-accent)',
                },
            },
        },
    },
    plugins: [],
}
