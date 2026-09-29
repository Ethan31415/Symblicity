# Symblicity

Symblicity is a tiny 8-bit esoteric language built from single-character
instructions, directional execution, selectable register banks, a double-ended
stack, case-paired jumps, and compact function-like control flow.

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

- `-u`, `--unbuffered` — immediate TTY input, with canonical buffering and echo disabled.
- `-B`, `--buffered` — normal/default terminal buffering.
- `-n`, `--nonblocking` — input returns 0 when no byte is available.
- `-b`, `--blocking` — wait for input (default).

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
itself has no audio-library build dependency.

If no sounds are loaded, `U`, `u`, `V`, and `v` retain their normal Symblicity
behavior as opposite-case directional letter jumps. `T/t` are reserved only
when sounds are loaded and dual-audio mode is enabled; otherwise they remain
ordinary directional letter jumps.

## Current language notes

The current VM includes:

- Five 8-bit registers (`R0`..`R4`) with selectable A/B banks.
- Shared result register `R2`.
- A double-ended stack.
- Two 256-byte memory spaces through `w/W/x/X` and `y/Y/z/Z`.
- Direction-sensitive case-pair letter jumps.
- Bidirectional `{}` execution.
- `[]` loops; **`~` breaks only the innermost enclosing `[]` loop**.
- Relative `#` control flow using A.
- Opposite-parenthesis return anchors.
- Character and numeric input/output through the selected A register.
- Optional asynchronous sound instructions.

See [docs/LANGUAGE.md](docs/LANGUAGE.md) for the instruction reference.

## Public domain

Symblicity is dedicated to the public domain under **CC0 1.0 Universal**.
You may copy, modify, distribute, embed, port, or sell it without asking
permission or providing attribution. See [LICENSE](LICENSE).

## Repository layout

```text
src/                 interpreter source
docs/                language documentation
examples/            small Symblicity programs
Makefile              normal build/install target
install.sh            user-local installer
uninstall.sh          user-local uninstaller
LICENSE               project license
```
