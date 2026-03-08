import { spawn } from 'child_process';
import path from 'path';

export default function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method not allowed' });
    }

    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: 'Query is required' });
    }

    // Path to the Python script
    // Adjust the path to navigate from: 
    // .../dashboard_app/.next/... or .../dashboard_app/pages/api 
    // to .../Member1_AI_Core/brain/spidy_brain.py
    // Simplest is to use the absolute path we know.
    const scriptPath = String.raw`c:\Users\Shandeesh R P\spidy\AI_Engine\brain\spidy_brain.py`;
    const pythonPath = "python"; // Assumes python is in PATH

    const pythonProcess = spawn(pythonPath, [scriptPath, query]);

    let dataString = '';
    let errorString = '';

    pythonProcess.stdout.on('data', (data) => {
        dataString += data.toString();
    });

    pythonProcess.stderr.on('data', (data) => {
        errorString += data.toString();
    });

    pythonProcess.on('close', (code) => {
        if (code !== 0) {
            console.error(`Python script exited with code ${code}`);
            console.error(`Stderr: ${errorString}`);
            return res.status(500).json({ error: 'AI Processing execution failed', details: errorString });
        }

        try {
            // The script prints JSON to stdout
            const jsonResponse = JSON.parse(dataString);
            res.status(200).json(jsonResponse);
        } catch (e) {
            console.error("Failed to parse JSON:", dataString);
            res.status(500).json({ error: 'Invalid response from AI Core', raw: dataString });
        }
    });
}
