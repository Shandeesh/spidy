const express = require('express');
const bodyParser = require('body-parser');
const cors = require('cors');
const { spawn } = require('child_process');
const path = require('path');

const http = require('http');
const { Server } = require("socket.io");

const app = express();
const server = http.createServer(app); // Create HTTP server
const PORT = 5000;

// Socket.io Setup
const io = new Server(server, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

app.use(cors());
app.use(bodyParser.json());

// Routes
app.get('/', (req, res) => {
    res.send('Spidy Backend is Running 🕷️');
});

io.on('connection', (socket) => {
    console.log('Frontend Client Connected:', socket.id);
});

const axios = require('axios'); // Add axios (assuming installed or use http)

// Main User Interaction Endpoint
app.post('/api/ask', async (req, res) => {
    const userQuery = req.body.query;

    if (!userQuery) {
        return res.status(400).json({ error: "Query is required" });
    }

    try {
        // Call Python Brain Server (Persistent)
        const brainUrl = 'http://127.0.0.1:5001/api/ask';
        const response = await axios.post(brainUrl, { query: userQuery });
        const decision = response.data;

        console.log("AI Decision:", decision);

        // If intent is AUTOMATION, trigger local automation script
        // Note: brain_server.py now handles execution internally, so we might not need to trigger it here
        // unless we want double execution? Let's assume brain_server handles it as per previous code.

        // However, if the brain server returns "execution_status", we just pass it along.

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

function triggerAutomation(details) {
    console.log(`Triggering Automation for: ${details}`);
    // Here we would call the Automation Engine (Bharath's module)
    // const autoScript = path.resolve(__dirname, '../automation_engine/app_control/launcher.py');
    // spawn('python', [autoScript, details]);
}

server.listen(PORT, () => {
    console.log(`Server running on http://localhost:${PORT}`);
});
