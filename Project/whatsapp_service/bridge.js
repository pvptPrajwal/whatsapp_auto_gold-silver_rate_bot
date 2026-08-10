const express = require('express');
const QRCode = require('qrcode');
const path = require('path');
const fs = require('fs');
const { Client, LocalAuth } = require('whatsapp-web.js');

const PORT = Number(process.env.WA_BRIDGE_PORT || 3001);
const ROOT_DIR = path.resolve(__dirname, '..');
const DATA_DIR = path.join(ROOT_DIR, 'data');
const AUTH_DIR = path.join(DATA_DIR, 'wwebjs_auth');
fs.mkdirSync(DATA_DIR, { recursive: true });
fs.mkdirSync(AUTH_DIR, { recursive: true });

const app = express();
app.use(express.json({ limit: '1mb' }));

let client = null;
let initializing = false;
let state = {
  status: 'starting',
  qr: null,
  phone: null,
  pushname: null,
  lastError: null,
  lastEvent: 'Service starting',
  updatedAt: new Date().toISOString()
};

function patchState(patch) {
  state = { ...state, ...patch, updatedAt: new Date().toISOString() };
  console.log(`[WA] ${state.status}: ${state.lastEvent || ''}`);
}

function safeId(id) {
  if (!id) return null;
  if (typeof id === 'string') return id;
  return id._serialized || id.user || null;
}

async function createClient() {
  if (initializing || client) return;
  initializing = true;
  patchState({ status: 'starting', lastEvent: 'Initializing WhatsApp background client', lastError: null });

  client = new Client({
    authStrategy: new LocalAuth({
      clientId: 'gold-silver-bot',
      dataPath: AUTH_DIR
    }),
    puppeteer: {
      headless: true,
      args: [
        '--no-sandbox',
        '--disable-setuid-sandbox',
        '--disable-dev-shm-usage',
        '--disable-gpu',
        '--window-size=1365,900'
      ]
    }
  });

  client.on('qr', async (qr) => {
    try {
      const qrData = await QRCode.toDataURL(qr, { width: 320, margin: 2 });
      patchState({
        status: 'qr_required',
        qr: qrData,
        lastEvent: 'Scan the QR code from WhatsApp > Linked devices',
        lastError: null
      });
    } catch (err) {
      patchState({ status: 'error', lastError: err.message, lastEvent: 'QR generation failed' });
    }
  });

  client.on('authenticated', () => {
    patchState({ status: 'authenticated', qr: null, lastEvent: 'WhatsApp authenticated. Loading account...' });
  });

  client.on('ready', () => {
    const info = client.info || {};
    patchState({
      status: 'connected',
      qr: null,
      phone: safeId(info.wid),
      pushname: info.pushname || null,
      lastError: null,
      lastEvent: 'WhatsApp connected and ready'
    });
  });

  client.on('auth_failure', (message) => {
    patchState({ status: 'auth_failure', qr: null, lastError: String(message), lastEvent: 'Saved WhatsApp session could not be authenticated' });
  });

  client.on('disconnected', async (reason) => {
    patchState({ status: 'disconnected', qr: null, lastError: String(reason), lastEvent: 'WhatsApp disconnected' });
    try { await client.destroy(); } catch (_) {}
    client = null;
    initializing = false;
  });

  try {
    await client.initialize();
  } catch (err) {
    patchState({ status: 'error', lastError: err.message, lastEvent: 'WhatsApp initialization failed' });
    try { await client.destroy(); } catch (_) {}
    client = null;
  } finally {
    initializing = false;
  }
}

async function ensureClient() {
  if (!client && !initializing) {
    createClient().catch((err) => {
      patchState({ status: 'error', lastError: err.message, lastEvent: 'Client startup failed' });
    });
  }
}

app.get('/health', (_req, res) => {
  res.json({ ok: true, service: 'gold-silver-whatsapp-bridge', status: state.status });
});

app.get('/status', async (_req, res) => {
  await ensureClient();
  res.json(state);
});

app.post('/connect', async (_req, res) => {
  await ensureClient();
  res.json({ ok: true, ...state });
});

app.get('/groups', async (_req, res) => {
  if (!client || state.status !== 'connected') {
    return res.status(409).json({ ok: false, error: 'WhatsApp is not connected.' });
  }
  try {
    const chats = await client.getChats();
    const groups = chats
      .filter((chat) => chat && chat.isGroup && chat.id && chat.id._serialized)
      .map((chat) => ({
        id: chat.id._serialized,
        name: chat.name || chat.formattedTitle || chat.id._serialized
      }))
      .sort((a, b) => a.name.localeCompare(b.name, undefined, { sensitivity: 'base' }));
    return res.json({ ok: true, groups });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/send', async (req, res) => {
  const { chatId, message } = req.body || {};
  if (!client || state.status !== 'connected') {
    return res.status(409).json({ ok: false, error: 'WhatsApp is not connected.' });
  }
  if (!chatId || typeof chatId !== 'string') {
    return res.status(400).json({ ok: false, error: 'chatId is required.' });
  }
  if (!chatId.endsWith('@g.us')) {
    return res.status(400).json({ ok: false, error: 'Selected chat is not a WhatsApp group ID.' });
  }
  if (!message || typeof message !== 'string') {
    return res.status(400).json({ ok: false, error: 'message is required.' });
  }

  try {
    const chat = await client.getChatById(chatId);
    if (!chat) {
      return res.status(404).json({ ok: false, error: 'WhatsApp group was not found.' });
    }
    if (!chat.isGroup) {
      return res.status(400).json({ ok: false, error: 'The selected chat is not a group.' });
    }
    const sent = await chat.sendMessage(message);
    return res.json({
      ok: true,
      messageId: sent && sent.id ? safeId(sent.id) : null,
      chatId,
      groupName: chat.name || null,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    patchState({ lastError: err.message, lastEvent: 'Message send failed' });
    return res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/logout', async (_req, res) => {
  try {
    if (client) {
      try { await client.logout(); } catch (_) {}
      try { await client.destroy(); } catch (_) {}
    }
    client = null;
    initializing = false;
    patchState({
      status: 'logged_out',
      qr: null,
      phone: null,
      pushname: null,
      lastError: null,
      lastEvent: 'WhatsApp session logged out'
    });
    setTimeout(() => ensureClient(), 800);
    return res.json({ ok: true });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

app.post('/restart', async (_req, res) => {
  try {
    if (client) {
      try { await client.destroy(); } catch (_) {}
    }
    client = null;
    initializing = false;
    patchState({ status: 'starting', qr: null, lastError: null, lastEvent: 'Restarting WhatsApp client' });
    ensureClient();
    return res.json({ ok: true });
  } catch (err) {
    return res.status(500).json({ ok: false, error: err.message });
  }
});

const server = app.listen(PORT, '127.0.0.1', () => {
  console.log(`[WA] Bridge listening on http://127.0.0.1:${PORT}`);
  ensureClient();
});

async function shutdown() {
  try {
    if (client) await client.destroy();
  } catch (_) {}
  server.close(() => process.exit(0));
  setTimeout(() => process.exit(0), 2500).unref();
}

process.on('SIGINT', shutdown);
process.on('SIGTERM', shutdown);
