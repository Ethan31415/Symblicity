from pathlib import Path
import base64
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
app_path = root / 'app.js'
sw_path = root / 'sw.js'
battle_path = root / 'examples' / 'battleship.sym'

app = app_path.read_text()
battle_b64 = base64.b64encode(battle_path.read_bytes()).decode('ascii')

# app.js used to construct SymblicityVM before the UI runtime-state variables
# existed. The VM constructor immediately invokes onState(), which called
# updateState() and touched `running` while it was still in the temporal dead
# zone. That aborts the whole module before any button listeners are attached.
state_block = """let running = false;
let waitTimer = null;
let renderPending = false;
let lastStateRender = 0;
"""
terminal_anchor = "const terminal = new Terminal(terminalEl);"
if app.find(state_block) > app.find(terminal_anchor):
    app = app.replace(state_block + "\n", "", 1)
    app = app.replace(terminal_anchor, state_block + "\n" + terminal_anchor, 1)

# Keep the one-click demo self-contained. The previous version fetched the game
# after the button was pressed, so a path/cache/network failure looked like a
# dead button.
if 'const BATTLESHIP_SOURCE = atob(' not in app:
    app = app.replace(
        "import { SymblicityVM } from './symblicity.js';\n",
        "import { SymblicityVM } from './symblicity.js';\n\n"
        "// Embedded at deploy time so Play Battleship never needs a second request.\n"
        f"const BATTLESHIP_SOURCE = atob('{battle_b64}');\n",
        1,
    )

# The original 12-second generated music buffer can hold up the UI noticeably
# on slower browsers. A shorter loop sounds the same once looped and starts much
# faster.
app = app.replace('    const seconds = 12;', '    const seconds = 4;', 1)

old_start = '''async function startProgram({ battleship = false } = {}) {
  try {
    stopProgram(false);
    await audio.unlock();
    if (battleship) {
      audioSel.value = 'battleship';
      await loadExample('battleship');
    }
    await prepareAudioFromSelection();
    audio.dual = true;
    terminal.reset();
    vm.reset(source.value);
    running = true;
    runBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus('Running', 'ok');
    terminalEl.focus();
    continueRun();
  } catch (err) {
    running = false;
    setStatus(err.message || String(err), 'error');
  }
}'''

new_start = '''async function startProgram({ battleship = false } = {}) {
  const oldLabel = playBattleshipBtn.textContent;
  try {
    if (battleship) {
      playBattleshipBtn.disabled = true;
      playBattleshipBtn.textContent = 'Starting Battleship...';
      setStatus('Starting Battleship...');
    }
    stopProgram(false);

    // Do this before the first await that is unrelated to audio. Browsers only
    // allow AudioContext resume reliably while handling the user's click.
    await audio.unlock();

    if (battleship) {
      audioSel.value = 'battleship';
      await loadExample('battleship');
    }
    await prepareAudioFromSelection();
    audio.dual = true;
    terminal.reset();
    vm.reset(source.value);
    running = true;
    runBtn.disabled = true;
    stopBtn.disabled = false;
    setStatus(battleship ? 'Battleship running -- use the terminal below' : 'Running', 'ok');
    if (battleship) {
      playBattleshipBtn.textContent = 'Restart Battleship';
      const panel = terminalEl.closest('.terminal-panel');
      if (panel) panel.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    terminalEl.focus({ preventScroll: true });
    continueRun();
  } catch (err) {
    running = false;
    setStatus(`Could not start: ${err.message || String(err)}`, 'error');
    playBattleshipBtn.textContent = oldLabel;
  } finally {
    playBattleshipBtn.disabled = false;
  }
}'''

if old_start in app:
    app = app.replace(old_start, new_start, 1)
elif 'Battleship running -- use the terminal below' not in app:
    raise SystemExit('Could not locate startProgram() in app.js')

old_load = '''  if (name === 'battleship') {
    const res = await fetch('examples/battleship.sym');
    if (!res.ok) throw new Error('Could not load Battleship example.');
    source.value = await res.text();
    audioSel.value = 'battleship';
    setStatus('Loaded Battleship');
  }'''
new_load = '''  if (name === 'battleship') {
    source.value = BATTLESHIP_SOURCE;
    exampleSel.value = 'battleship';
    audioSel.value = 'battleship';
    setStatus('Loaded Battleship');
  }'''
if old_load in app:
    app = app.replace(old_load, new_load, 1)
elif 'source.value = BATTLESHIP_SOURCE;' not in app:
    raise SystemExit('Could not locate Battleship loader in app.js')

old_listener = "playBattleshipBtn.addEventListener('click', () => startProgram({ battleship: true }));"
new_listener = '''playBattleshipBtn.addEventListener('click', async () => {
  try { await startProgram({ battleship: true }); }
  catch (err) { setStatus(`Could not start: ${err.message || String(err)}`, 'error'); }
});'''
if old_listener in app:
    app = app.replace(old_listener, new_listener, 1)

# The VM constructor immediately emits an initial state through onState().
# updateState() reads these variables, so they must exist before new SymblicityVM().
state_old = """const terminal = new Terminal(terminalEl);
const audio = new BrowserAudio();
const vm = new SymblicityVM({"""
state_new = """let running = false;
let waitTimer = null;
let renderPending = false;
let lastStateRender = 0;

const terminal = new Terminal(terminalEl);
const audio = new BrowserAudio();
const vm = new SymblicityVM({"""
if state_old in app:
    app = app.replace(state_old, state_new, 1)

late_state = """let running = false;
let waitTimer = null;
let renderPending = false;
let lastStateRender = 0;

function setStatus"""
if late_state in app:
    app = app.replace(late_state, "function setStatus", 1)

# Deployment smoke guard: if this invariant is broken, fail the workflow instead
# of publishing a page whose controls never initialize.
if app.index("let running = false;") > app.index("new SymblicityVM("):
    raise SystemExit("Browser startup invariant failed: running initialized after VM")

app_path.write_text(app)

# Force browsers off the first cached JS bundle and prefer fresh HTML/JS/CSS.
sw = sw_path.read_text()
sw = sw.replace("const CACHE = 'symblicity-web-v1';", "const CACHE = 'symblicity-web-v3';")
old_fetch = '''self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request).then(res => {
    const copy = res.clone();
    caches.open(CACHE).then(cache => cache.put(event.request, copy));
    return res;
  })));
});'''
new_fetch = '''self.addEventListener('fetch', event => {
  if (event.request.method !== 'GET') return;
  const url = new URL(event.request.url);
  const fresh = event.request.mode === 'navigate' || /\\.(?:js|css)$/.test(url.pathname);
  if (fresh) {
    event.respondWith(fetch(event.request).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(cache => cache.put(event.request, copy));
      return res;
    }).catch(() => caches.match(event.request)));
    return;
  }
  event.respondWith(caches.match(event.request).then(hit => hit || fetch(event.request).then(res => {
    const copy = res.clone();
    caches.open(CACHE).then(cache => cache.put(event.request, copy));
    return res;
  })));
});'''
if old_fetch in sw:
    sw = sw.replace(old_fetch, new_fetch, 1)
sw_path.write_text(sw)

print('Patched', app_path)
print('Patched', sw_path)
