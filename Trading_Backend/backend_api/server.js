/**
 * Spidy Backend API - Node.js Relay Server
 * 
 * PURPOSE (Flaw #15 Documentation):
 * This server acts as a lightweight RELAY between the Frontend Dashboard (port 3000)
 * and the Python AI Brain Server (port 5001). It provides:
 * 
 * 1. Socket.IO WebSocket server for real-time frontend communication
 * 2. REST proxy for /api/ask → Brain Server (port 5001)
 * 3. CORS handling for cross-origin requests
 * 
 * The frontend's AI chat feature sends user queries here, which are forwarded
 * to the Brain Server for processing. Trading data (status, positions, orders)
 * flows directly from the MT5 Bridge (port 8000) to the frontend, bypassing this server.
 * 
 * Port Map:
 *   3000 - Frontend Dashboard (Next.js)
 *   5000 - THIS SERVER (Node.js Relay)
 *   5001 - AI Brain Server (Python/FastAPI)
 *   8000 - MT5 Bridge Server (Python/FastAPI)
 */

const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const http = require('http');
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app);
const PORT = 5000;

// FIX #3: Restrict CORS to known local origins (was wildcard "*")
const ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://localhost:5001",
    "http://127.0.0.1:5001",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
];

// Socket.io Setup
const io = new Server(server, {
    cors: {
        origin: ALLOWED_ORIGINS,
        methods: ["GET", "POST"]
    }
});

app.use(cors({ origin: ALLOWED_ORIGINS }));
app.use(bodyParser.json());

// Routes
app.get('/', (req, res) => {
    res.send('Spidy Backend Relay Server 🕷️ (AI Chat Proxy + Socket.IO)');
});

io.on('connection', (socket) => {
    console.log('Frontend Client Connected:', socket.id);
    socket.on('disconnect', () => {
        console.log('Frontend Client Disconnected:', socket.id);
    });
});

const axios = require('axios');

// Main User Interaction Endpoint (Proxies to AI Brain Server)
app.post('/api/ask', async (req, res) => {
    const userQuery = req.body.query;

    if (!userQuery) {
        return res.status(400).json({ error: "Query is required" });
    }

    try {
        // Forward to Python Brain Server (port 5001)
        const brainUrl = 'http://127.0.0.1:5001/api/ask';
        const response = await axios.post(brainUrl, req.body);
        const decision = response.data;

        console.log("AI Decision:", decision);

        res.json({ success: true, ai_response: decision });

    } catch (error) {
        console.error("AI Request Failed:", error.message);
        if (error.response) {
            console.error("Brain Response:", error.response.data);
            res.status(500).json({ error: "AI Server Error", details: error.response.data });
        } else {
            res.status(500).json({ error: "AI Server Unreachable", details: error.message });
        }
    }
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({
        status: 'ok',
        role: 'AI Chat Relay + Socket.IO',
        uptime: process.uptime(),
        connected_clients: io.sockets.sockets.size
    });
});

server.listen(PORT, () => {
    console.log(`Spidy Relay Server running on http://localhost:${PORT}`);
    console.log(`Role: AI Chat Proxy (→ Brain:5001) + Socket.IO Hub`);
});
