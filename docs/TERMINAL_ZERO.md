# Terminal Zero groundwork

The current Terminal Zero shell is a Symblicity-native animated main menu and the
foundation for the roguelike engine.

## Main menu

Run it with:

```sh
sym -u --input-wait 80 examples/terminal_zero.sym
```

The menu targets a 100x36 terminal, enters the alternate screen, hides the cursor,
and restores the terminal on EXIT.

The main screen uses the exact TERMINAL ZERO logo and large four-line menu art:

```text
START
LOAD
HELP
EXIT
```

Each menu item is drawn inside a tight four-row word-sized box. Every redraw first
paints the entire box green-on-default, including padding, which clears any previous
selection background. If that item is selected, its four rows are then repainted
white-on-green. The result is one solid rectangular highlight around the ASCII word,
not disconnected background patches behind individual strokes.

Controls:

```text
W / S       move selection
E / Enter   select
```

### Menu rendering invariant

Selected rows are conditional independently, keeping every source-position skip
well below the one-byte `#` limit. No conditional skips across an entire four-row
ASCII block.

## Binary stream animation

The old fixed edge columns have been replaced by 20 independent binary streams.
Every visible data glyph is either `0` or `1`.

Each stream has an 8-byte record at `0x0400`:

```text
+0  next head row
+1  next binary bit
+2  column
+3  first row
+4  row range
+5  visible trail length
+6  speed
+7  phase
```

Streams have different lengths and update at 1x, 1/2x, or 1/3x speed. The outer
streams run the full terminal height. Interior streams begin below the logo so the
title stays readable while the lower screen remains active. Old tail cells are
erased as heads advance, so the effect is a moving set of short vertical binary
trails rather than permanent columns.

The initial stream positions and bit phases are mixed from the read-only
`0xFEFF` wrapped system-time byte.

## Menu layout

```text
TERMINAL ZERO logo: row 2,  col 8
START:              row 16, col 36
LOAD:               row 20, col 36
HELP:               row 24, col 36
EXIT:               row 28, col 36
control hint:       row 33, col 38
```

Colors:

```text
binary streams      ANSI 32 / bright heads 92
title               ANSI 97
normal menu         ANSI 32
selected menu       ANSI 97;42
control hint        ANSI 2;32
```

## Runtime memory

```text
0x0200  menu selection
0x0201  last input byte
0x0202  exit flag
0x0203  animation frame
0x0204  animation seed
0x0205  scratch row
0x0206  scratch column
0x0207  scratch glyph
0x0209  audio event
0x020A  current stream-record pointer

0x0300  entity 0 type
0x0301  entity 0 x
0x0302  entity 0 y
0x0303  entity 0 width
0x0304  entity 0 height
0x0305  entity animation frame
0x0306  entity flags
0x0310  pending movement direction

0x0400-0x049F  20 binary stream records
```

The initial entity remains a 3x3 player-sized entity so the game engine is not
locked to one-character roguelike actors.

## Subroutines

```text
a  initial terminal/menu setup
b  draw menu art and current highlight
c  animation tick
d  input dispatcher
f  update one binary stream
g  help screen
h  selection up
i  selection down
j  activate selection
k  START/core placeholder
l  LOAD placeholder
n  exit request
o  terminal cleanup
p  entity initialization
q  redraw title/menu screen
r  entity movement core
s  audio-state initialization
```

The helper order is intentionally acyclic so directional letter lookup and the
nested parenthesis return stack remain well-defined.
