# Symblicity language reference

This document tracks the interpreter in `src/symblicity.c`.

## Machine state

- Five 8-bit registers: `R0`..`R4`.
- Selected bank 0: A=`R0`, B=`R1`.
- Selected bank 1: A=`R3`, B=`R4`.
- `R2` is the shared result register.
- All arithmetic wraps to 8 bits.
- The stack is a double-ended byte deque.

## Immediate digits

```text
0  +1
1  +2
2  +4
3  +8
4  +16
5  +32
6  +64
7  +128
8  -1
9  -2
```

Digits modify the selected A register.

## Arithmetic

`+ - * / % ^ | &` operate on A and B and write R2.
Division or modulo by zero yields 0.

## Comparison and skips

- `=` skip next instruction when A == B.
- `<` skip next instruction when A < B.
- `>` skip next instruction when A > B.
- `!` skip next instruction when A != B.
- `?` skip next instruction when R2 == 0.
- A literal ASCII space always skips the next instruction in the current execution direction.

## Registers

- `:` swaps A and B.
- `;` swaps B and R2.
- `\\` toggles the selected register bank.

## Stack

- `@` pushes A at the selected stack end.
- `$` pops the selected stack end into A. Empty pop yields 0.
- `_` toggles which end both push and pop use.

## I/O

- `'` reads one byte into A.
- `"` writes A as one byte.
- `.` reads a decimal byte value.
- `,` writes the current numeric A value.

## Memory

Symblicity has one 65,536-byte memory space addressed by two 8-bit address registers.

```text
address = (high << 8) | low
```

- `w`: low address byte = A
- `W`: A = low address byte
- `y`: high address byte = A
- `Y`: A = high address byte
- `x`: memory[address] = A
- `X`: A = memory[address]

The top 256 bytes, `0xFF00-0xFFFF`, remain ordinary memory but are also the
file-name buffer used by `z/Z`.

## File I/O

`z/Z` provide one stateful binary file stream.

- The file name is a NUL-terminated byte string beginning at memory address `0xFF00`.
- The maximum file name is 255 bytes.
- The first `Z` opens an existing file for binary read/write access and reads one byte.
- The first `z` opens an existing file for binary read/write access, or creates it if it does not exist, then writes A.
- `Z` reads the next byte into A.
- `z` writes A at the current file position.
- Reads and writes share one advancing file position.
- If the file-name bytes change, the current file is closed and the newly named file is opened from position 0 on the next `z/Z`.
- Successful reads and writes set `R2 = 0`.
- Reading at EOF sets `R2 = 1` and leaves A unchanged.
- File-system/open/read/write failures are VM errors.
- Files are closed automatically when the native VM exits.

The native VM accesses host files directly. The browser VM uses a persistent,
origin-local sandbox backed by browser storage; browser file names therefore name
sandbox files rather than arbitrary host paths.

### Legacy two-bank compatibility

Older programs that used the original two independent 256-byte memories can opt
into a compatibility map with a tab-comment directive:

```text
<TAB>@memory legacy-2x256
```

The directive is detected before preprocessing and the complete comment line is
then removed, so it contributes zero executable instruction positions.

In this mode:

```text
w/W + x/X -> unified memory page 0x00 (0x0000-0x00FF)
y/Y + z/Z -> unified memory page 0x01 (0x0100-0x01FF)
```

This is how the bundled Battleship program preserves its original memory layout.
Programs without the directive use the normal combined 16-bit address model and `z/Z` file I/O.

All eight letters remain reserved and do not perform case-pair jumps.

## Control flow

- `{` forces forward execution.
- `}` forces backward execution.
- `[` / `]` form repeating loops.
- `~` breaks only the innermost enclosing `[]` loop. Outside a loop it is a no-op.
- `#` advances A+1 source positions in the current execution direction.
- `(` and `)` use a dedicated 4096-entry return stack. When empty, the first encountered parenthesis becomes the caller character and pushes its current position. While active, the same caller character pushes more positions; the opposite parenthesis pops and immediately resumes at `saved_position + current_direction`. One caller character is shared by the whole stack and is cleared when the stack becomes empty.
- Backtick clears A.
- Other letters jump to the next opposite-case occurrence in the current execution direction. No target means the letter is skipped.

A tab begins a source comment through the physical end of line. Newlines, carriage returns,
form feed, and vertical tab are formatting only.

## Optional asynchronous sound

Start the VM with:

```sh
sym --sounds ./sounds program.sym
```

Files in the directory are sorted alphabetically and become the VM sound array.

While at least one sound is loaded:

- `U`: select the next sound, wrapping.
- `u`: select the previous sound, wrapping.
- `V`: asynchronously start the selected sound on channel 1.
- `v`: stop channel 1.

When `--dual-audio` / `-2` is enabled:

- `T`: asynchronously start the currently selected sound on channel 2.
- `t`: stop channel 2.
- Both channels use the same shared sound address selected by `U/u`.
- The channels play independently, so two sounds can overlap.

Playback is implemented through `ffplay` and therefore requires FFmpeg when sound is used.

If no sounds are loaded, `U/u/V/v` are not reserved: they retain ordinary Symblicity
opposite-case letter-jump behavior. `T/t` are reserved only when sounds are
loaded and dual-audio mode is enabled; otherwise they remain normal case-pair jumps.


## Configurable input wait

```sh
sym -u --input-wait 80 program.sym
```

The interpreter-wide input wait applies to both `'` character input and `.` numeric input:

- `--input-wait infinite` or `--input-wait -1`: block indefinitely (default).
- `--input-wait 0`: nonblocking poll.
- `--input-wait N`: wait up to N milliseconds whenever the instruction needs more input, where N is 0..60000.
- `--input-timeout` is retained as a compatibility alias.

Infinite mode preserves the original input semantics and leaves R2 unchanged.
In finite/nonblocking mode, a completed input writes the value to A and sets
R2=1. Timeout or EOF sets R2=0, leaves A unchanged, and completes the input
instruction. A partial numeric token is discarded if it times out.

The browser playground exposes the same setting as **Input wait (ms)**, with
`-1` meaning infinite. The built-in Battleship example selects 80 ms so a
standalone ESC can be distinguished from a multi-byte arrow-key escape sequence
without a busy loop.

## Programming conventions

The VM rules above are separate from the project's standard source-layout and function idioms. Large programs conventionally use `m/M` to skip a function bank at startup, `e/E` to skip a second function bank at exit, and can give the same letter pair different forward- and backward-direction implementations.

See [CONVENTIONS.md](CONVENTIONS.md) for the current standard program layout, directional function overloading, parenthesis return patterns, the canonical backward-entered function convention, and the A/`#` return trampoline.
