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

The workflow updates daily at 06:23 America/Fortaleza (09:23 UTC), on generator
changes, or manually from
Actions. GitHub scheduling and contribution processing can delay updates.
Generated commits are authored by github-actions[bot].

Run from the repository root with Python 3.9+ and an authenticated GitHub CLI:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/update_streak.py
```

## Public and private language statistics

`update_languages.py` generates `assets/languages.svg` from GitHub's language
API. It reads repository metadata and byte counts, not source files. It scans
all pages of the owner's repositories, including private and archived projects;
forks and the profile repository itself are excluded. New repositories and
languages are discovered automatically. Every language gets a label, and the
card grows when more labels are needed.

Percentages represent each language's share of the total code bytes reported
by GitHub, not proficiency or authorship. This replaces the previous hosted
card's mixed byte/repository-count weighting. Jupyter Notebook includes notebook
files as GitHub classifies them. Published SVG data and successful workflow logs
contain only aggregate languages and percentages, without private repository
names or source. API errors retain the previous image, including when a token
can see only public repositories. There is no fallback that silently removes
private languages.

The workflow runs daily at **06:37 America/Fortaleza (09:37 UTC)**, on generator
changes, and manually. It commits only when the generated image changes. GitHub
may delay scheduled runs, and language detection may take time after a push.
Public-repository scheduled workflows can be disabled after 60 days without
repository activity; re-enable the workflow in Actions when GitHub requests it.
Both profile asset workflows share a concurrency group to avoid competing
publishes.

### One-time private metadata access

The built-in Actions token cannot read the owner's other private repositories.
Create a separate fine-grained personal access token:

1. Open [fine-grained tokens](https://github.com/settings/personal-access-tokens/new).
   Name it `Profile language statistics` and set resource owner to `maxsampa`.
2. Choose **All repositories** so future private projects are included too.
   Keep only **Metadata: Read-only**, which GitHub selects automatically;
   do not add Contents or write permissions. Choose an expiration date and
   renew the secret when it expires.
3. Copy the token directly into a new repository secret named
   **`PROFILE_STATS_TOKEN`** under
   [maxsampa → Settings → Secrets and variables → Actions](https://github.com/maxsampa/maxsampa/settings/secrets/actions).
   Do not paste it into a README, source file, issue, or chat.
4. Open [Update language statistics](https://github.com/maxsampa/maxsampa/actions/workflows/update-languages.yml)
   and click **Run workflow** on `main`. Subsequent updates are automatic and
   do not depend on this computer being on.

The read-only token is passed only to the language generator. Checkout and
publishing use the profile repository's built-in `GITHUB_TOKEN`. Never put the
personal token into an SVG URL. Without the secret, the workflow explicitly
fails with setup instructions and leaves the published snapshot unchanged.

For a local refresh with an authenticated GitHub CLI belonging to the owner:

```sh
python3 -m unittest discover -s scripts -p 'test_*.py'
python3 scripts/update_languages.py
```

References: [language API and Metadata permission](https://docs.github.com/en/rest/repos/repos#list-repository-languages),
[GitHub Actions secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets),
and [scheduled workflows](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
