# Symblicity coding conventions

This document records the standard source-layout and function idioms currently used by Symblicity programs. These are conventions built from the core VM instructions; they are not additional instructions or parser rules.

## Source formatting

Symblicity source is a one-dimensional instruction stream even when it is written across many physical lines.

- Newline, carriage return, form feed, and vertical tab are formatting only.
- A literal ASCII space is executable: it skips the next instruction in the current execution direction. Do not use spaces merely for indentation.
- TAB starts a comment through the physical end of the line. Use TAB only when the rest of that physical line is intended to be a comment.
- Blank lines are safe because newlines are removed.
- Normal termination is falling off either end of the source.

When a convention is shown schematically with words such as `<body>`, those words are placeholders, not literal Symblicity source.

## Standard whole-program layout

The standard large-program layout reserves `m/M` for entry and `e/E` for exit:

```text
m
<backward function bank>
M
<main program>
e
<forward function bank>
E
```

Execution initially moves forward.

1. The initial `m` jumps to the next `M`, skipping the backward-function bank.
2. Main executes after `M`.
3. Reaching `e` jumps to the final `E`, skipping the forward-function bank.
4. Execution then falls off the end of the source.

Under this convention, `m/M` and `e/E` are control-flow guards and should not be allocated as ordinary user-function names.

The older generated Battleship programs already use the first half of this layout:

```text
m<backward functions>M<main>
```

The `e...E` half extends the same idea to a second function bank below/after main.

## Directional function overloading

Letter jumps search only in the current execution direction. That means a single call letter can select two different implementations.

For the pair `a/A`:

```text
direction = -1:  a -> nearest A to the left
direction = +1:  a -> nearest A to the right
```

With the standard layout, one `A` entry can live in the backward-function bank and another `A` entry can live in the forward-function bank:

```text
m
<backward a body> A
...
M
<main containing a calls>
e
A <forward a body>
...
E
```

A call written simply as `a` therefore means:

```text
(a, backward direction) -> backward implementation
(a, forward direction)  -> forward implementation
```

The effective function identity is the pair `(letter, execution direction)` rather than the letter alone. This can approximately double the usable function namespace without adding any VM instructions.

The same rule works for other non-reserved letter pairs. Keep the intended matching entry as the nearest opposite-case occurrence in that direction.

## Parenthesis return anchors

`(` and `)` provide the standard lightweight return mechanism.

- If no return marker exists, the encountered parenthesis saves its own position and type.
- Encountering the opposite parenthesis returns to the saved position and consumes the marker.
- Encountering the same parenthesis type again replaces the saved position.
- The mechanism is independent of execution direction.

This is one typed return marker, not an automatic call stack. Nested function calls therefore require manual state management or a convention specifically designed for nesting.

Both orientations are valid:

```text
( ... )
) ... (
```

The opening symbol is whichever symbol establishes the anchor first; the opposite symbol performs the return.

## Canonical backward-entered function convention

The compact generators used by the larger Symblicity programs use a canonical backward-entered function convention.

For function pair `A/a`, the stored definition has this shape:

```text
{( 1`<reversed-body>a
```

and a call has this exact shape:

```text
`)#A}
```

The literal space in the definition is intentional Symblicity source; it is not formatting.

Generator form:

```python
def call(letter):
    emit('`)#' + letter.upper() + '}')

def define(letter, body):
    definitions.append('{( 1`' + body[::-1] + letter.lower())
```

The body is physically reversed because the function is entered and executed right-to-left. The current canonical use keeps these functions straight-line so their reverse execution does not create loop-direction ambiguity.

This convention is especially useful for compact reusable output and helper routines. Because the VM has only one parenthesis return marker, the established generated code avoids nested calls inside these functions.

## A/# return-trampoline convention

A second compact function idiom uses A as a one-bit call/return state and `#` as a trampoline. A concrete example is:

```text
`(#a




e
A

5434"""""

`0)
E
```

Newlines are ignored, so this is one instruction stream.

The control flow is:

1. Backtick clears A.
2. `(` saves the return anchor.
3. With A = 0, `#` advances one position to `a`.
4. `a` jumps to the matching `A` function entry.
5. The function body runs.
6. `` `0 `` leaves A = 1.
7. `)` returns to the saved `(`.
8. On the second pass A = 1, so `#` advances two positions and skips the call.
9. `e` jumps to `E`, bypassing the inline function region.

In the example, `5434` constructs ASCII 72 and the five quote instructions output `HHHHH`.

The general idea is:

```text
A = 0 -> # selects the call path
A = 1 -> # selects the post-return path
```

This is useful when an inline function and its continuation need to occupy the same compact source region.

## Function-letter availability

Always reserved by the VM:

```text
w/W  y/Y      16-bit address bytes
x/X  z/Z      aliases for the same unified memory access
```

The duplicated `x/X` and `z/Z` data-access pairs are intentional for now.
One pair is reserved for a future additional address-byte extension.

Reserved by the standard program-layout convention:

```text
m/M  e/E
```

Conditionally reserved by audio:

```text
U/u  V/v       when sounds are loaded
T/t            when sounds are loaded and dual-audio is enabled
```

When the relevant audio mode is disabled those audio letters revert to ordinary directional letter jumps. Programs intended to run unchanged with and without audio should avoid using `t/T`, `u/U`, or `v/V` as function names.

Every other available opposite-case pair can participate in the directional overloading convention.

## Direction-sensitive helper rules

Several control-flow instructions are relative to the current direction and should be treated that way inside functions:

- `#` moves A+1 source positions in the current direction.
- `{` forces forward execution; `}` forces backward execution.
- `[]` is the repeating loop construct.
- `~` exits only the innermost enclosing `[]` loop; it does not exit a `{}` directional region.
- Ordinary letter lookup always searches in the current direction.

This is why the established backward-entered helper convention favors straight-line function bodies unless the function deliberately accounts for reverse loop behavior.

## Register and stack calling convention

No universal argument-register, return-register, stack-frame, or register-preservation ABI has been standardized yet.

Current VM rules still apply:

- A is the selected primary register and is used by character/numeric I/O.
- B is the selected secondary operand register.
- R2 is the shared arithmetic/result register.
- `\` swaps between the R0/R1 and R3/R4 A/B banks.
- `@/$/_` provide the double-ended byte stack.

Individual programs may establish stricter register, memory, or stack conventions, but those are program-specific until promoted into this document.
