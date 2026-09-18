# Contribution streak card

`update_streak.py` reads the GitHub contribution calendar for every year since
account creation and generates `assets/contribution-streak.svg`.

- The longest streak is measured in consecutive calendar days with activity.
- Equal-length streaks are resolved in favor of the most recent ending date.
- Today can remain empty without breaking yesterday's current streak.
- Dates always include the year; the current day uses America/Fortaleza.
- Data visibility follows the GitHub token used by `gh`. Actions uses its built-in
  token, with no personal access token or private repository access required.
- Failed or incomplete API responses leave the previous card intact.

The workflow updates every six hours, on generator changes, or manually from
Actions. GitHub scheduling and contribution processing can delay updates.
Generated commits are authored by github-actions[bot].

Run from the repository root with Python 3.9+ and an authenticated GitHub CLI:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/update_streak.py
```
