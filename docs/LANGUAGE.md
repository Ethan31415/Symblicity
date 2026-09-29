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

Two independent 256-byte spaces are available:

- `w`: address-W = A
- `W`: A = address-W
- `x`: mem-W[address-W] = A
- `X`: A = mem-W[address-W]
- `y`: address-Y = A
- `Y`: A = address-Y
- `z`: mem-Y[address-Y] = A
- `Z`: A = mem-Y[address-Y]

These letters are reserved and do not perform case-pair jumps.

## Control flow

- `{` forces forward execution.
- `}` forces backward execution.
- `[` / `]` form repeating loops.
- `~` breaks only the innermost enclosing `[]` loop. Outside a loop it is a no-op.
- `#` advances A+1 source positions in the current execution direction.
- `(` and `)` form an opposite-symbol return-anchor mechanism.
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
- `V`: asynchronously start the selected sound.
- `v`: stop the currently playing sound.

Playback is implemented through `ffplay` and therefore requires FFmpeg when sound is used.

If no sounds are loaded, `U/u/V/v` are not reserved: they retain ordinary Symblicity
opposite-case letter-jump behavior.
