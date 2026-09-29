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

The installer writes to `~/.local/bin/sym` by default.

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
```

Files in the directory are loaded into a deterministic, alphabetically sorted
sound array. When at least one sound is loaded:

- `U` selects the next sound, wrapping at the end.
- `u` selects the previous sound, wrapping at the beginning.
- `V` starts the selected sound asynchronously.
- `v` stops the currently playing sound.

Playback uses `ffplay`, so install FFmpeg if you want sound. The interpreter
itself has no audio-library build dependency.

If no sounds are loaded, `U`, `u`, `V`, and `v` retain their normal Symblicity
behavior as opposite-case directional letter jump.

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
