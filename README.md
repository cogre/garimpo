# garimpo

Searches GitHub for projects close to what you are building and hands you a short list to read.

*Garimpo* is Portuguese for prospecting: sifting a lot of gravel for a little gold.

One file, standard library only. It uses GitHub's public search API: read-only, no account, and it never
downloads, installs or runs anything it finds.

## Why

GitHub's trending page shows what everybody is looking at. I wanted the opposite: a list made from my own
questions, that only shows me something again when it has actually changed.

The point is to find **ideas**, not dependencies. In the first days I used it, I read six repositories it
surfaced, installed none of them, and came out with seventeen ideas worth writing down. Three of them were
built right away as small pieces of my own code.

## Use

Requires Python 3.8 or newer.

1. Edit `themes.txt`. One search per line, as `THEME | words`:

   ```
   VIDEO   | text to video ffmpeg
   NOTES   | local-first notes markdown
   AGENTS  | topic:mcp-server python
   FRESH   | @new 7
   ```

2. Run it:

   ```
   python garimpo.py
   ```

3. Read `found/YYYY-MM-DD.md`: up to six repositories per theme, each with description, stars, language,
   license, last push and creation date.

A run takes about 7 seconds per search, because the API allows 10 unauthenticated searches a minute. Set a
`GITHUB_TOKEN` environment variable if you want a higher limit; it is optional and only read, never stored.

`python garimpo.py --all` also lists what already showed up in earlier runs.

## How it chooses

- **Filters added to every search:** 60 to 60,000 stars, pushed to in the last 90 days, not archived, and the
  words must be in the name, description or topics. Above 60,000 stars you already know the project.
- **`@new N`** ignores the words and asks for repositories created in the last N days, by stars.
- **Only news:** `seen.json` remembers every repository and its stars on each run. A repository is listed when
  it is new, or when it grew at least 10% and 100 stars since last time.
- **Order:** a simple score from stars (log scale), stars per day of life, days since last push, and growth.
  A young project climbing fast ranks above an old one standing still.
- **Dropped:** "awesome" lists and other lists of links.

The numbers are constants at the top of `garimpo.py`.

## What it does not do

- **Judge quality.** Stars can be bought and a README promises whatever it wants.
- **Protect you.** Some categories attract code that steals credentials; trading bots are the classic one.
  Read before you run anything, and never run a stranger's bot with a real wallet or key.
- **Search inside code or READMEs.** Only name, description and topics, so a vague description hides a project.
- **Find things with long queries.** GitHub requires every word to match. Three words is usually the limit.

## What worked for me

- Short searches. `net worth tracker` finds more than a sentence does.
- One theme for things outside your field. The best idea so far came from a repository about something
  unrelated.
- Changing `themes.txt` after every run. A search that brought noise twice gets replaced.
- Writing each idea down with where it came from, and keeping the list short.

## Tests

```
python -m unittest discover -s tests
```

The tests run offline, with a fake search.

## License

MIT
