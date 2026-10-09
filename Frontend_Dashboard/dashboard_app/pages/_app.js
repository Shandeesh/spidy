import '../styles/globals.css';
import axios from 'axios';

// The API key is supplied only by the local deployment environment. Never
// embed a control credential in the browser bundle or source repository.
axios.interceptors.request.use((config) => {
    const apiKey = process.env.NEXT_PUBLIC_SPIDY_API_KEY;
    if (apiKey) {
        config.headers['X-API-KEY'] = apiKey;
    }
    return config;
}, (error) => {
    return Promise.reject(error);
});

function MyApp({ Component, pageProps }) {
    return <Component {...pageProps} />;
}

export default MyApp;
