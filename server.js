const { spawn } = require('child_process');
const path = require('path');

const backendDirectory = path.join(__dirname, 'Trading_Backend', 'backend_api');
const backend = spawn(process.execPath, ['server.js'], {
	cwd: backendDirectory,
	stdio: 'inherit',
	env: process.env,
});

const shutdown = (signal) => {
	if (!backend.killed) {
		backend.kill(signal);
	}
};

process.on('SIGINT', () => shutdown('SIGINT'));
process.on('SIGTERM', () => shutdown('SIGTERM'));
backend.on('exit', (code, signal) => {
	process.exitCode = code ?? (signal ? 1 : 0);
});
