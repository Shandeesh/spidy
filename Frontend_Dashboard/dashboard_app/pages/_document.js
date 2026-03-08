import { Html, Head, Main, NextScript } from 'next/document'

export default function Document() {
    return (
        <Html lang="en">
            <Head>
                <link rel="icon" href="/favicon.ico" />
                <link rel="apple-touch-icon" href="/logo.png" />
                <link rel="manifest" href="/manifest.json" />
                <meta name="description" content="Spidy AI Trading Interface" />
                <meta name="theme-color" content="#000000" />
            </Head>
            <body>
                <Main />
                <NextScript />
            </body>
        </Html>
    )
}
