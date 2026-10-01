# Symblicity

Symblicity is a tiny 8-bit esoteric language built from single-character
instructions, directional execution, selectable register banks, a double-ended
stack, case-paired jumps, and compact function-like control flow.

## Try it online

Open the browser playground:

**https://ethan31415.github.io/Symblicity/**

The web VM runs entirely in the browser and includes the editor, terminal,
register/state display, local `.sym` loading, Web Audio support, and a one-click
Battleship demo. It does not require a compiler, FFmpeg, `ffplay`, or terminal
configuration.

## Build

```sh
make
./bin/sym examples/hello.sym
```

Or install the `sym` command for the current user:

```sh
./install.sh
sym examples/hello.sym
```

The installer writes to `~/.local/bin/sym` by default. If `ffplay` is not
already available, it asks whether you want it to install FFmpeg using the detected
system package manager. The default answer is **No**, so no extra system package is
installed without explicit permission.

## Run

```sh
sym program.sym
```

Interactive programs can use immediate terminal input:

```sh
sym -u -b program.sym
```

- `-u`, `--unbuffered` -- immediate TTY input, with canonical buffering and echo disabled.
- `-B`, `--buffered` -- normal/default terminal buffering.
- `-n`, `--nonblocking` -- alias for `--input-wait 0`.
- `-b`, `--blocking` -- alias for `--input-wait infinite` (default).
- `--input-wait infinite` / `--input-wait -1` -- preserve the traditional blocking input behavior.
- `--input-wait 0` -- poll input without waiting.
- `--input-wait N` -- wait up to N milliseconds (0..60000) whenever character or numeric input needs more data.
- `--input-timeout` remains as a compatibility alias for `--input-wait`.

In finite/nonblocking mode, successful `'` or `.` input sets R2 to 1. A timeout or EOF sets R2 to 0 and leaves A unchanged. Infinite mode preserves the original semantics and does not modify R2. The browser playground exposes the same value as an **Input wait** control; Battleship selects 80 ms by default.

## Asynchronous sound

Pass a directory of sound files to the VM:

```sh
sym --sounds ./sounds program.sym

# Optional second playback channel
sym --sounds ./sounds --dual-audio program.sym
```

Files in the directory are loaded into a deterministic, alphabetically sorted
sound array. When at least one sound is loaded:

- `U` selects the next sound, wrapping at the end.
- `u` selects the previous sound, wrapping at the beginning.
- `V` starts the selected sound asynchronously on channel 1.
- `v` stops channel 1.

With `--dual-audio` (or `-2`) enabled:

- `T` starts the same currently selected sound on channel 2.
- `t` stops channel 2.
- Both channels share the one sound address controlled by `U/u`.
- `VT` starts the same sound on both channels simultaneously.
- `VUT` starts the current sound on channel 1, moves to the next address,
  then starts that sound on channel 2.

Playback uses `ffplay`, so install FFmpeg if you want sound. The interpreter
itself has no audio-library build dependency. The player is detached from terminal
input and playback errors are no longer suppressed.

The browser VM maps the same audio instructions to the Web Audio API instead,
so the online version has no native audio dependency.

If no sounds are loaded, `U`, `u`, `V`, and `v` retain their normal Symblicity
behavior as opposite-case directional letter jumps. `T/t` are reserved only
when sounds are loaded and dual-audio mode is enabled; otherwise they remain
ordinary directional letter jumps.

## Current language notes

The current VM includes:

- Five 8-bit registers (`R0`..`R4`) with selectable A/B banks.
- Shared result register `R2`.
- A double-ended stack.
- One 65,536-byte memory space with a combined 16-bit address: `w/W` controls the low byte, `y/Y` the high byte, and `x/X` read/write memory. Address `0xFEFF` is a read-only live clock byte containing Unix milliseconds modulo 256. `z/Z` provide a stateful binary file stream whose NUL-terminated filename lives at `0xFF00`. Native programs access host files; the browser uses persistent sandboxed storage. Legacy programs can use `@memory legacy-2x256` to retain the original page-0/page-1 `x/X` and `z/Z` behavior; bundled Battleship uses this mode.
- Direction-sensitive case-pair letter jumps.
- Bidirectional `{}` execution.
- `[]` loops; **`~` breaks only the innermost enclosing `[]` loop**.
- Relative `#` control flow using A.
- A dedicated 4096-entry parenthesis return stack for nested calls and recursion.
- Character and numeric input/output through the selected A register.
- Optional asynchronous sound instructions.
- Directional function overloading: the same letter pair can select different forward and backward implementations.
- Conventional `m...M` main entry and `e...E` program exit guards.

See [docs/LANGUAGE.md](docs/LANGUAGE.md) for the instruction reference and [docs/CONVENTIONS.md](docs/CONVENTIONS.md) for the standard program-layout and function conventions.

## Terminal Zero demo

The in-progress roguelike demo lives at `examples/terminal_zero.sym`. Its first
foundation includes the animated binary main menu, nested helper routines, and the
initial multi-cell entity/movement memory layout. Run it with:

```sh
sym -u --input-wait 80 examples/terminal_zero.sym
```

See [docs/TERMINAL_ZERO.md](docs/TERMINAL_ZERO.md) for the current engine layout.

## Browser playground

The complete static browser site is stored in `web/site.tar.gz` and deployed by
`.github/workflows/pages.yml`. The archive contains the JavaScript VM core, editor,
ANSI terminal renderer, Battleship example, PWA files, and Web Audio integration.
See `web/README.md` for local extraction instructions.

Built-in Battleship audio uses the same deterministic OGG assets as the native game. The Pages workflow generates those assets from `web/make_battleship_sounds.py`, and the browser decodes them through Web Audio. End users do not need FFmpeg installed. Users can also load their own local audio files as a sorted Symblicity sound array.

## Public domain

Symblicity is dedicated to the public domain under **CC0 1.0 Universal**.
You may copy, modify, distribute, embed, port, or sell it without asking
permission or providing attribution. See [LICENSE](LICENSE).

## Repository layout

```text
src/                  native C interpreter
docs/                 language reference and coding conventions
web/                  browser playground archive
examples/             small native Symblicity programs
.github/workflows/    GitHub Pages deployment
Makefile               normal build/install target
install.sh             user-local installer
uninstall.sh           user-local uninstaller
LICENSE                public-domain dedication
```
