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

// ── Agent Event Bridge ────────────────────────────────────────────────────────
// Receives events from BusBridgeAgent (Python agents/bus_bridge.py) and
// broadcasts them to every connected frontend client via Socket.IO.
//
// Each message has the shape:
//   { topic: string, sender: string, age_ms: number, data: object }
//
// The frontend can listen to individual topics:
//   socket.on('market_snapshot', handler)
//   socket.on('sentiment', handler)
//   socket.on('risk_state', handler)
//   socket.on('trade_signal', handler)
//   socket.on('execution_report', handler)
//
// AND a catch-all:
//   socket.on('agent_event', handler)   ← receives every topic
// ─────────────────────────────────────────────────────────────────────────────

const VALID_TOPICS = new Set([
    'market_snapshot', 'sentiment', 'risk_state',
    'trade_signal', 'execution_report'
]);

// Rolling in-memory cache — one latest message per topic (for new joiners)
const latestByTopic = {};

app.post('/agent-event', (req, res) => {
    const event = req.body;

    if (!event || !event.topic || !event.data) {
        return res.status(400).json({ error: 'Missing topic or data' });
    }

    if (!VALID_TOPICS.has(event.topic)) {
        return res.status(400).json({ error: `Unknown topic: ${event.topic}` });
    }

    // Cache for late-joining clients
    latestByTopic[event.topic] = event;

    // Emit topic-specific channel + universal channel
    io.emit(event.topic, event);
    io.emit('agent_event', event);

    res.status(204).end();
});

// Send cached latest state to a newly connected client
io.on('connection', (socket) => {
    console.log('Frontend Client Connected:', socket.id);

    // Immediately replay latest known state per topic
    for (const cached of Object.values(latestByTopic)) {
        socket.emit(cached.topic, cached);
        socket.emit('agent_event', cached);
    }

    socket.on('disconnect', () => {
        console.log('Frontend Client Disconnected:', socket.id);
    });
});

const axios = require('axios');

// ── AI Chat Proxy ─────────────────────────────────────────────────────────────
// Forwards /api/ask queries from the frontend to the Python Brain Server (5001)
app.post('/api/ask', async (req, res) => {
    const userQuery = req.body.query;

    if (!userQuery) {
        return res.status(400).json({ error: 'Query is required' });
    }

    try {
        const brainUrl = 'http://127.0.0.1:5001/api/ask';
        const response = await axios.post(brainUrl, req.body);
        console.log('AI Decision:', response.data);
        res.json({ success: true, ai_response: response.data });
    } catch (error) {
        console.error('AI Request Failed:', error.message);
        if (error.response) {
            res.status(500).json({ error: 'AI Server Error', details: error.response.data });
        } else {
            res.status(500).json({ error: 'AI Server Unreachable', details: error.message });
        }
    }
});

// ── Health check ──────────────────────────────────────────────────────────────
app.get('/health', (req, res) => {
    res.json({
        status:              'ok',
        role:                'AI Chat Proxy + Socket.IO + Agent Event Bridge',
        uptime:              process.uptime(),
        connected_clients:   io.sockets.sockets.size,
        agent_topics_seen:   Object.keys(latestByTopic),
    });
});

server.listen(PORT, () => {
    console.log(`Spidy Relay Server running on http://localhost:${PORT}`);
    console.log(`Role: AI Chat Proxy (→ Brain:5001) + Socket.IO + Agent Bridge`);
});
