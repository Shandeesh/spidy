import '../styles/globals.css';
import axios from 'axios';

// Add global API Key to all Axios requests
axios.interceptors.request.use((config) => {
    config.headers['X-API-KEY'] = "spidy_secure_123";
    return config;
}, (error) => {
    return Promise.reject(error);
});

function MyApp({ Component, pageProps }) {
    return <Component {...pageProps} />;
}

export default MyApp;
