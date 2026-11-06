# How to change this profile

Almost everything lives in one file: `.profile/shop.toml`. Edit it, run one command, look at the result.

You need Python 3.11 or newer, the GitHub CLI (`gh`) logged in, and:

```bash
pip install fonttools brotli
```

## The commands

Run these from the top of the repo.

| What | Command |
| --- | --- |
| Rebuild and open a preview | `python .profile/build.py --preview` |
| Same, without asking GitHub for new numbers | `python .profile/build.py --preview --offline` |
| Same, without opening a browser | add `--no-open` |
| Fail on any `WARN` | add `--strict` (files and preview are still written, so you can look) |
| List what you changed since the last publish | `python .profile/build.py --publish` |
| Rebuild, commit and push. Any `WARN` stops it before the commit | `python .profile/build.py --publish --yes` |
| Show bio and repo description changes | `python .profile/build.py --apply-github` |
| Apply those changes | `python .profile/build.py --apply-github --yes` |

The preview is a fake GitHub page, dark and light, in `.profile/preview/`. That folder never gets uploaded.

The PNG pictures are stills, so moving parts don't show: only the first tape message appears, and the eyes on the closer stay hidden. Open the HTML page to see them move.

Going live takes two commands if you changed the bio or a repo description: `--publish --yes` for the page, `--apply-github --yes` for those.

If publishing says your changes clash with GitHub, the same lines were changed in both places, and nothing was published. Open `shop.toml`, find the `<<<<<<<` marks, keep the version you want, delete the marks, run `git stash drop`, and publish again.

Never edit `README.md` or anything in `assets/` by hand. Every build overwrites them. A card you take off the page has its pictures deleted.

## Common jobs

**Change any wording.** Find the sentence in `shop.toml` and change it. Paragraphs wrap by themselves. Short single lines, like the ones on the hero, don't. If a line runs out of its space, the build prints a `WARN` saying which one and by how much. Warnings can't see everything, so always look at the preview too.

**Change your name or Discord.** Edit the `[shop]` section. Every card picks it up.

**Change the page order or remove a card.** Edit the `page` list at the top. Move a line, or delete it.

- `"keys-a + keys-b"` puts cards side by side.
- `"seanime 76%"` makes a card narrower.

**Add a project.** Copy a whole card block, give it a new name and add that name to `page`:

```toml
[cards.mything]
style = "work_order"
repo = "my-repo-name"
name_size = 60
fits = ["Fits: Discord", "Made of: TypeScript"]
rows = [
  ["Came in with", "What the problem was."],
  ["What I did", "What you built."],
]
back = "Yes."
warning = "Anything people must know before using it."
sticker_width = 730
sticker_tilt = 0.8
```

Stars and the link are filled in from `repo`. Optional extras: `note`, `stamp`, `smudge = true`, `under_fits`, `back_rows`, `side_note`, `side_size`, `side_step`. If the name is too long, lower `name_size`. The `vortex` card uses 50 for a 23 letter name.

Smaller projects can use `style = "drawer"` (see `rscripts`) or `style = "loaner"` for forks (see `seanime`).

**Remove a project.** Delete its line from `page` and its `[cards.x]` block. `skip_in_stats` is separate from cards. A repo listed there doesn't count toward the language numbers, whether or not it has a card. Forks never count.

**Add a section heading.** Copy `[cards.label-main]`, change `words`, and add it to `page`.

**Change colours.** `[theme.dark]` and `[theme.light]` hold the colours that differ between GitHub's dark and light modes. `[colors]` holds the ones shared by both, like steel, amber and the pencil purple.

There are two blues, both in `[colors]`. `brand_blue` is the sign plates, stamps, links and "Goes back?" text. `bright_blue` is the hazard stripes and the eyes behind the closed door.

**Change fonts.** Put the `.ttf` in `.profile/fonts/` and point to it in `[fonts]`. Widths are measured from the real font, so run with `--strict` afterwards to catch anything that no longer fits. Then look at the preview too: a wider font can crowd things the warnings can't see, like stamps and signs. Static fonts only, and check the licence allows embedding.

**Add a colour of your own.** Add a line to `[colors]` and use it in a drawing as `§your_name`.

**Change the avatar.** Put a square webp, png or jpg of about 320 px in `.profile/` and set `avatar` in `[shop]`. Keep it small, since it's stored inside the hero picture. GitHub's own round profile photo is separate, and you change that on GitHub.

**Change the bio or a repo's About text.** Edit `[github]`, then run `--apply-github`. Limits are 160 characters for the bio and 350 for a description. A repo that isn't listed is left alone. If GitHub refuses the bio change, run `gh auth refresh -s user` once.

**Change the words on work orders.** `Work order`, `Goes back?`, `Get it`, `Warning` and `Stars` are in `[labels]`.

## Live numbers you can use in any text

Write these in curly brackets and the build fills them in. They work in cards, `[labels]`, `footer`, the bio and repo descriptions.

| Token | Gives |
| --- | --- |
| `{owner}` `{login}` `{discord}` `{discord_id}` | your `[shop]` settings |
| `{repos}` `{followers}` `{stars_total}` `{contributions}` | counts from GitHub |
| `{date}` | day the numbers were last fetched from GitHub (UTC) |
| `{stars_REPO}` | stars on one repo, like `{stars_cordmuffin}` |
| `{lua_REPO}` | Lua size of one repo, like `{lua_RScripts}` |

A GitHub Action (`.github/workflows/shop.yml`) rebuilds once a day, so the numbers stay fresh without you.

## What each style can hold

These are fixed drawings with room for a set amount. Going over the count gives a `WARN`.

| Style | Room for |
| --- | --- |
| `hero` | 1 name, 2 lines, any number of tape messages (they take turns), 4 spots on the tool wall (`hammer`, `screwdriver`, `roller`, `wrench` for the empty outline) |
| `key` | a small word and a big word |
| `shelf_label` | one heading |
| `work_order` | grows with the text |
| `drawer` | 5 short lines |
| `loaner` | about 3 lines |
| `manual` | grows with the text |
| `rules` | 2 rules of 2 lines each, plus the scrawled one |
| `stock` | 4 bins |
| `timecard` | 3 columns |
| `closer` | about 6 lines of note |

## Starting over with a whole new look

The wording, colours, fonts and order are settings. The shapes are not: the pegboard, tags, drawer and door are drawn by the functions in `build.py`, one per style.

For a new look with new shapes:

1. Write a new function in `build.py`, above the `STYLES` list. This is a whole working style:

```python
def sticky(th, d, o):
    c = Card(o["_id"], 400, 200, th)
    c.add(f'<rect x="10" y="10" width="380" height="180" fill="{th["paper"]}" filter="url(#paper)"/>')
    c.text(30, 60, o["title"], "s", 36, th["ink"])
    y = 100
    for line in wrap(o["text"], "c", 20, 340):
        c.text(30, y, line, "c", 20, th["ink"])
        y += 27
    c.scrawl(30, 170, o["note"], 32)
    c.alt = [o["title"], o["text"], o["note"]]
    return c
```

2. Add it to `STYLES`: `"sticky": sticky,`
3. Add a `[cards.x]` block with `style = "sticky"` and its settings, and put `x` on the `page` list.

What you need to know:

- `th` is the current theme's colours, `d` the live numbers, `o` that card's settings from `shop.toml`.
- `c.text(x, y, words, font, size, colour)`. Fonts are `"c"` typewriter, `"b"` typewriter bold, `"s"` stencil, `"r"` handwriting. Add `limit=number` to warn when text passes that x position.
- `c.scrawl` is the handwriting shortcut. `c.add` takes raw SVG. `wrap(text, font, size, width)` splits a paragraph into lines.
- `c.alt` is a list of the card's words for screen readers.
- Shared effects: `filter="url(#paper)"`, `url(#drop)`, `url(#small)`, `url(#brushed)`, `url(#stamp)`. Shared fills: `url(#steel)`, `url(#steelh)`, `url(#blade)`, `url(#hazard)`.

Everything else keeps working: fonts, dark and light, overflow warnings, numbers, the preview and publishing. Old styles can be deleted once no card uses them.

Colours in a drawing are written as `§name` and looked up in `shop.toml`.

## House rules for the words

- No em or en dashes. The build refuses them.
- Keep project facts true. Jokes go on Pops, never on what a tool does.
- No code comments in `build.py`. Explanations go here.
