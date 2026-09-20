// Holds a persistent native-messaging port to the Codexalgia host, which
// pushes Codex's status whenever it changes. An open port also keeps
// this service worker alive.
const HOST = 'com.tpojka.codexalgia';
const RECONNECT_ALARM = 'reconnect';

const ICONS = {
  busy: 'hip-pain',
  ready: 'hip-ok',
  unknown: 'hip-unknown',
};

let port = null;

function iconSet(name) {
  const set = {};
  for (const size of [16, 32, 48, 128]) set[size] = `icons/${name}-${size}.png`;
  return set;
}

function render(state, detail) {
  const titles = {
    busy: 'Codex is working…',
    ready: 'Codex is ready',
    unknown: 'Codexalgia: native host not connected',
  };
  chrome.action.setIcon({ path: iconSet(ICONS[state] || ICONS.unknown) });
  chrome.action.setTitle({ title: detail ? `${titles[state]}\n${detail}` : titles[state] });
}

function describe(msg) {
  const { busy = 0, total = 0 } = msg;
  if (total === 0) return 'No active sessions';
  return `${busy} of ${total} session${total === 1 ? '' : 's'} working`;
}

function connect() {
  if (port) return;
  try {
    port = chrome.runtime.connectNative(HOST);
  } catch (e) {
    port = null;
    render('unknown', String(e));
    return;
  }
  port.onMessage.addListener((msg) => {
    render(msg.state === 'busy' ? 'busy' : 'ready', describe(msg));
  });
  port.onDisconnect.addListener(() => {
    const err = chrome.runtime.lastError;
    port = null;
    render('unknown', err ? err.message : 'Disconnected');
  });
}

chrome.alarms.create(RECONNECT_ALARM, { periodInMinutes: 0.5 });
chrome.alarms.onAlarm.addListener((alarm) => {
  if (alarm.name === RECONNECT_ALARM) connect();
});
chrome.runtime.onStartup.addListener(connect);
chrome.runtime.onInstalled.addListener(connect);
chrome.action.onClicked.addListener(connect);

connect();
