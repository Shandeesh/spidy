import { spawn } from 'child_process';
import path from 'path';

import fs from 'fs';

export default function handler(req, res) {
    if (req.method !== 'POST') {
        return res.status(405).json({ message: 'Method not allowed' });
    }

    const { query } = req.body;

    if (!query) {
        return res.status(400).json({ error: 'Query is required' });
    }

    const rootPath = path.resolve(process.cwd(), '..', '..');
    const scriptPath = path.join(rootPath, 'AI_Engine', 'brain', 'spidy_brain.py');
    
    let pythonPath = 'python';
    const venvPythonPath = path.join(rootPath, '.venv', 'Scripts', 'python.exe');
    if (fs.existsSync(venvPythonPath)) {
        pythonPath = venvPythonPath;
    }

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
