# Graded String Arrangements

A free, public website: hymns and carols arranged in six levels for violin, viola, cello and bass,
with a play-along reader for each piece.

## What's here

- `index.html` – the home page, with the list of pieces.
- `songs/<piece>/index.html` – the reader for one piece; `songs/<piece>/<piece>.xml` is its score.
- `assets/` – shared by every piece: the music font (Bravura) and the string sounds (GeneralUser GS),
  each with its licence file.

It is a plain static site: no build step. Vercel (or any static host) serves the folder as it is.

## Adding a piece

1. Add `songs/<new-piece>/` with its reader page and score.
2. Add a card for it to the list in `index.html`.

## Credits

Music drawn and played with alphaTab (alphatab.net, MPL-2.0). Bravura music font, SIL Open Font
License. String sounds from the GeneralUser GS sound bank by S. Christian Collins.
