const { app, BrowserWindow } = require('electron');
const { spawn } = require('child_process');
const path = require('path');

let mainWindow;
let pythonProcess;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1200,
    height: 800,
    backgroundColor: '#000000',
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true
    },
    frame: true,
    title: 'Ultron AI v5.7',
    icon: path.join(__dirname, 'public', 'icon.png') // Optional: Add icon
  });

  // Load the React app
  // In development: http://localhost:3000
  // In production: file://path/to/dist/index.html
  const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;
  
  if (isDev) {
    mainWindow.loadURL('http://localhost:3000');
    mainWindow.webContents.openDevTools(); // Enable DevTools in development
  } else {
    mainWindow.loadFile(path.join(__dirname, 'dist', 'index.html'));
  }

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function startPythonBackend() {
  const backendPath = path.join(__dirname, '..', 'backend', 'server.py');
  const pythonExecutable = 'python'; // Or 'python3' on some systems
  
  console.log('Starting Python backend:', backendPath);
  
  pythonProcess = spawn(pythonExecutable, [backendPath], {
    cwd: path.join(__dirname, '..', 'backend')
  });

  pythonProcess.stdout.on('data', (data) => {
    console.log(`[Python Backend] ${data.toString()}`);
  });

  pythonProcess.stderr.on('data', (data) => {
    console.error(`[Python Backend Error] ${data.toString()}`);
  });

  pythonProcess.on('close', (code) => {
    console.log(`Python backend exited with code ${code}`);
  });
}

function stopPythonBackend() {
  if (pythonProcess) {
    console.log('Stopping Python backend...');
    pythonProcess.kill();
    pythonProcess = null;
  }
}

app.on('ready', () => {
  // Start Python backend first
  startPythonBackend();
  
  // Wait 2 seconds for backend to initialize, then open window
  setTimeout(() => {
    createWindow();
  }, 2000);
});

app.on('window-all-closed', () => {
  stopPythonBackend();
  if (process.platform !== 'darwin') {
    app.quit();
  }
});

app.on('activate', () => {
  if (mainWindow === null) {
    createWindow();
  }
});

app.on('before-quit', () => {
  stopPythonBackend();
});

// Handle app crashes gracefully
process.on('uncaughtException', (error) => {
  console.error('Uncaught Exception:', error);
  stopPythonBackend();
});
