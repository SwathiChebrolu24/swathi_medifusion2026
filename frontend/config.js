// Configuration for API and WebSocket URLs
const IS_LOCALHOST = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1";

const BACKEND_URL = IS_LOCALHOST ? "http://localhost:8000" : "https://project1-backend-8wnx.onrender.com";

const API_BASE_URL = BACKEND_URL;
const WS_BASE_URL = BACKEND_URL.replace(/^http/, 'ws');

console.log(`🔧 Config loaded: API=${API_BASE_URL}, WS=${WS_BASE_URL}`);
