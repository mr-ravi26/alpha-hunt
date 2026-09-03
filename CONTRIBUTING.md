# Contributing

Thanks for considering a contribution! This project is a personal job-search
automation tool that's open-sourced so others can adapt it — contributions
that make it more general-purpose, more reliable, or easier to set up are
very welcome.

## Before you start

- For anything non-trivial (new ATS support, new source, behavior changes),
  open an issue first to discuss the approach before writing code.
- Small fixes (typos, docs, bug fixes) can go straight to a PR.

## Development setup

```bash
git clone https://github.com/<your-fork>/alpha-hunt.git
cd alpha-hunt
pip install -r requirements.txt
playwright install --with-deps chromium
cp qa_template.yaml qa.yaml   # fill with test values, do not commit
```

Never commit `config.yaml` with real personal details, `qa.yaml`, your
resume, or any file under `data/` other than `.gitkeep` — these are
gitignored on purpose. See [.gitignore](.gitignore).

## Making changes

- Keep PRs focused — one logical change per PR.
- Match the existing code style (see `src/*.py`).
- If you're adding support for a new ATS (job board provider), keep the
  fetch/apply logic isolated the way `sources.py` / `apply.py` already
  separate Greenhouse/Lever/Ashby.
- Test locally with `python src/main.py` against a real (or sandboxed)
  `qa.yaml` before submitting, since form-filling logic is easy to break
  silently.

## Submitting a PR

1. Fork the repo and create a branch off `main`.
2. Make your changes and verify nothing in `data/`, `config.yaml` (with real
   values), or `qa.yaml` is staged (`git status` before committing).
3. Open a PR using the template — describe what changed and why.

## Reporting bugs / requesting features

Please use the issue templates under **Issues → New Issue**.

## Questions

Open a [Discussion](../../discussions) or an issue — happy to help.
