from pathlib import Path
import base64
import re
import sys

root = Path(sys.argv[1] if len(sys.argv) > 1 else '_site')
app_path = root / 'app.js'
sw_path = root / 'sw.js'
battle_path = root / 'examples' / 'battleship.sym'
repo_battle_path = Path('examples/battleship.sym')

# Keep the deployed simulator's Battleship source in sync with the canonical
# repository example instead of the older copy packed inside site.tar.gz.
battle_path.write_bytes(repo_battle_path.read_bytes())

app = app_path.read_text()
battle_b64 = base64.b64encode(battle_path.read_bytes()).decode('ascii')

# app.js used to construct SymblicityVM before the UI runtime-state variables
# existed. The VM constructor immediately invokes onState(), so these variables
# must exist before the VM is constructed. Make this transformation idempotent:
# remove every existing copy, then insert exactly one copy before Terminal/VM init.
state_block = """let running = false;
let waitTimer = null;
let renderPending = false;
let lastStateRender = 0;
"""
terminal_anchor = "const terminal = new Terminal(terminalEl);"
app = app.replace(state_block, "")
if terminal_anchor not in app:
    raise SystemExit("Could not locate terminal initialization in app.js")
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

# Final startup-state canonicalization. Earlier transforms may modify the
# surrounding code, so remove every declaration block and insert exactly one
# immediately before terminal/audio/VM construction.
state_decl_re = re.compile(
    r"let running = false;\n"
    r"let waitTimer = null;\n"
    r"let renderPending = false;\n"
    r"let lastStateRender = 0;\n+"
)
app = state_decl_re.sub("", app)
terminal_anchor = "const terminal = new Terminal(terminalEl);"
if terminal_anchor not in app:
    raise SystemExit("Could not locate terminal initialization in app.js")
app = app.replace(terminal_anchor, state_block + "\n" + terminal_anchor, 1)

if "let timedCharInput = false;" not in app:
    app = app.replace(
        "let lastStateRender = 0;\n\nconst terminal = new Terminal(terminalEl);",
        "let lastStateRender = 0;\nlet timedCharInput = false;\n\nconst terminal = new Terminal(terminalEl);",
        1,
    )

if app.count("let running = false;") != 1:
    raise SystemExit("Browser startup invariant failed: duplicate running declarations")
if app.index("let running = false;") > app.index("new SymblicityVM("):
    raise SystemExit("Browser startup invariant failed: running initialized after VM")

# Firefox and other browsers may suspend Web Audio between the initiating click
# and the VM's later T/V opcode. Make play() self-healing, make the background
# clearly audible, and start Battleship music explicitly during launch.
old_play_guard = """  play(channel, selected = this.selected) {
    if (!this.context || !this.buffers[selected]) return;
    this.stop(channel);
"""
new_play_guard = """  play(channel, selected = this.selected) {
    if (!this.context || !this.buffers[selected]) return;
    if (this.context.state !== 'running') {
      this.context.resume().then(() => this.play(channel, selected)).catch(err => {
        this.error = err.message || String(err);
        updateAudioState();
      });
      return;
    }
    this.stop(channel);
"""
if old_play_guard in app:
    app = app.replace(old_play_guard, new_play_guard, 1)

old_background_end = """      data[i] = v * env;
    }
    return buffer;
  }"""
new_background_end = """      data[i] = v * env;
    }
    let peak = 0;
    for (let i = 0; i < data.length; i++) peak = Math.max(peak, Math.abs(data[i]));
    if (peak > 0) {
      const scale = 0.82 / peak;
      for (let i = 0; i < data.length; i++) data[i] *= scale;
    }
    return buffer;
  }"""
if old_background_end in app:
    app = app.replace(old_background_end, new_background_end, 1)

app = app.replace(
    "gain.gain.value = selected === 0 && channel === 1 ? 0.55 : 0.9;",
    "gain.gain.value = selected === 0 && channel === 1 ? 1.0 : 0.9;",
    1,
)

old_audio_state = """  const name = audio.names[audio.selected] || `#${audio.selected}`;
  audioStateEl.textContent = `Audio: ${audio.count} sounds | selected ${audio.selected}: ${name}`;
}"""
new_audio_state = """  const name = audio.names[audio.selected] || `#${audio.selected}`;
  const contextState = audio.context ? audio.context.state : 'none';
  const active = [];
  if (audio.channels[0]) active.push('ch1');
  if (audio.channels[1]) active.push('ch2');
  audioStateEl.textContent = `Audio: ${contextState} | ${audio.count} sounds | selected ${audio.selected}: ${name} | playing ${active.join('+') || 'none'}`;
}"""
if old_audio_state in app:
    app = app.replace(old_audio_state, new_audio_state, 1)

old_prepare = """    await prepareAudioFromSelection();
    audio.dual = true;
    terminal.reset();"""
new_prepare = """    await prepareAudioFromSelection();
    audio.dual = true;
    if (battleship && audio.count) {
      audio.selected = 0;
      audio.play(1, 0);
    }
    terminal.reset();"""
if old_prepare in app:
    app = app.replace(old_prepare, new_prepare, 1)

# Only Battleship needs the 80 ms zero-byte timeout for distinguishing a
# standalone ESC from an arrow-key escape sequence. Ordinary Symblicity programs
# should block at character input until the user actually types something.
app = app.replace(
    "    stopProgram(false);\n\n    // Do this before the first await",
    "    stopProgram(false);\n    timedCharInput = battleship || exampleSel.value === 'battleship';\n\n    // Do this before the first await",
    1,
)
app = app.replace(
    "    if (result.status === 'wait_char') {",
    "    if (result.status === 'wait_char' && timedCharInput) {",
    1,
)

# Replace the synthesized built-in audio with the exact OGG assets generated
# from the same deterministic source used by the native Battleship package.
old_builtin = """  async loadBuiltIn() {
    this.loading = true; this.error = ''; updateAudioState();
    try {
      await this.unlock();
      this.stopAll();
      this.names = ['00_background', '01_menu_nav', '02_menu_select', '03_hit', '04_sunk'];
      this.buffers = [
        this.backgroundBuffer(),
        this.toneBuffer([660, 880], 0.07, 'sine', 0.5),
        this.toneBuffer([440, 660, 880], 0.14, 'triangle', 0.45),
        this.toneBuffer([110, 73.42], 0.20, 'triangle', 0.65),
        this.toneBuffer([196, 146.83, 98], 0.52, 'triangle', 0.6),
      ];
      this.selected = 0;
    } catch (err) {
      this.error = err.message || String(err);
      this.buffers = []; this.names = [];
      throw err;
    } finally {
      this.loading = false; updateAudioState();
    }
  }"""
new_builtin = """  async loadBuiltIn() {
    this.loading = true; this.error = ''; updateAudioState();
    try {
      await this.unlock();
      this.stopAll();
      const files = [
        '00_background.ogg',
        '01_menu_nav.ogg',
        '02_menu_select.ogg',
        '03_hit.ogg',
        '04_sunk.ogg',
      ];
      const decoded = [];
      for (const file of files) {
        const response = await fetch('./audio/' + file, { cache: 'no-store' });
        if (!response.ok) throw new Error('Could not load ' + file);
        decoded.push(await this.decode(file.replace(/\\.ogg$/, ''), await response.arrayBuffer()));
      }
      this.names = decoded.map(x => x.name);
      this.buffers = decoded.map(x => x.buffer);
      this.selected = 0;
    } catch (err) {
      this.error = err.message || String(err);
      this.buffers = []; this.names = [];
      throw err;
    } finally {
      this.loading = false; updateAudioState();
    }
  }"""
if old_builtin in app:
    app = app.replace(old_builtin, new_builtin, 1)
elif "fetch('./audio/' + file" not in app:
    raise SystemExit("Could not locate built-in audio loader")

# Stop registering the old PWA service worker. It caused stale app.js files to
# survive multiple otherwise-correct deployments.
app = app.replace(
    "if ('serviceWorker' in navigator) navigator.serviceWorker.register('./sw.js').catch(() => {});\n",
    "",
)
app_path.write_text(app)

# Publish versioned module filenames. Even a still-active old cache has never
# seen these URLs, so it must go to the network.
release = "v9"
vm_source = (root / "symblicity.js").read_text()
versioned_vm = root / f"symblicity-{release}.js"
versioned_app = root / f"app-{release}.js"
versioned_vm.write_text(vm_source)
versioned_app.write_text(
    app.replace(
        "from './symblicity.js';",
        f"from './symblicity-{release}.js';",
        1,
    )
)

# The fresh HTML proactively removes every old worker/cache before loading the
# new versioned application module.
index_path = root / "index.html"
index = index_path.read_text()
cleanup = """  <script>
    if ('serviceWorker' in navigator) {
      navigator.serviceWorker.getRegistrations()
        .then(regs => Promise.all(regs.map(reg => reg.unregister())))
        .catch(() => {});
    }
    if ('caches' in window) {
      caches.keys()
        .then(keys => Promise.all(keys.map(key => caches.delete(key))))
        .catch(() => {});
    }
  </script>
"""
index = index.replace(
    '  <script type="module" src="app.js"></script>',
    cleanup + f'  <script type="module" src="app-{release}.js"></script>',
    1,
)
index_path.write_text(index)

# If a browser does independently check the old worker URL, make the replacement
# worker remove itself and all legacy caches rather than caching anything else.
sw_path.write_text("""self.addEventListener('install', event => {
  event.waitUntil(self.skipWaiting());
});
self.addEventListener('activate', event => {
  event.waitUntil(Promise.all([
    self.registration.unregister(),
    caches.keys().then(keys => Promise.all(keys.map(key => caches.delete(key)))),
    self.clients.claim()
  ]));
});
self.addEventListener('fetch', () => {});
""")

print('Patched', app_path)
print('Created', versioned_app)
print('Created', versioned_vm)
print('Patched', index_path)
print('Disabled legacy service worker', sw_path)
