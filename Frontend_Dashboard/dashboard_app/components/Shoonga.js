import React, { useState, useEffect } from 'react';
import axios from 'axios';
import ShoongaDashboard from './shoonga/ShoongaDashboard';

export default function Shoonga() {
    // Real State for Shoonya Bridge
    const [status, setStatus] = useState({
        connected: false,
        shoonya_balance: "0.00",
        shoonya_equity: "0.00",
        shoonya_profit: "0.00",
        positions: []
    });
    const [logs, setLogs] = useState(["Connecting to Cloud Logs..."]);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                // Connect to Shoonya Server on PORT 8001
                const res = await axios.get('http://localhost:8001/status');
                if (res.data) {
                    setStatus(res.data);
                }
            } catch (e) {
                console.error("Shoonya Bridge Offline", e);
                setStatus(prev => ({ ...prev, connected: false }));
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 1000);

        // Log Websocket
        let ws;
        try {
            ws = new WebSocket('ws://localhost:8001/ws/logs');
            ws.onopen = () => setLogs(prev => ["Connected to Cloud Stream...", ...prev]);
            ws.onmessage = (event) => {
                setLogs(prev => [event.data, ...prev].slice(0, 100)); // Keep last 100
            };
            ws.onerror = (e) => console.log("WS Error", e);
        } catch (e) {
            console.error("WS Connection Failed", e);
        }

        return () => {
            clearInterval(interval);
            if (ws) ws.close();
        };
    }, []);

    return (
        <div className="h-full w-full">
            <ShoongaDashboard
                mt5Status={status} // Passing Shoonya status as mt5Status prop for compatibility
                logs={logs}
            />
        </div>
    );
}
