"""Publish aggregate language usage from owned public and private repositories."""
import argparse
from collections import Counter
from html import escape
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile


COLORS = {
    'Python': '#3572A5', 'Jupyter Notebook': '#DA5B0B', 'Kotlin': '#A97BFF',
    'Java': '#b07219', 'JavaScript': '#f1e05a', 'TypeScript': '#3178c6',
    'HTML': '#e34c26', 'CSS': '#663399', 'Shell': '#89e051',
    'Dart': '#00B4AB', 'Swift': '#F05138', 'C++': '#f34b7d',
    'C': '#555555', 'Rust': '#dea584', 'Go': '#00ADD8',
}


def api(endpoint, parameters=None, paginate=False):
    args = ['gh', 'api', endpoint, '--method', 'GET']
    for key, value in (parameters or {}).items():
        args.extend(['-f', f'{key}={value}'])
    if paginate:
        args.extend(['--paginate', '--slurp'])
    try:
        result = subprocess.run(args, capture_output=True, text=True, timeout=120)
    except subprocess.TimeoutExpired:
        raise RuntimeError('GitHub API timed out; the previous card was kept.') from None
    if result.returncode:
        # Do not copy CLI errors into public logs: endpoints can contain private names.
        raise RuntimeError('GitHub API request failed; the previous card was kept.')
    return json.loads(result.stdout)


def fetch_languages(username):
    if not re.fullmatch(r'[A-Za-z0-9-]+', username):
        raise ValueError('Invalid GitHub username')
    identity = api('user')
    if identity.get('login', '').casefold() != username.casefold():
        raise RuntimeError('Use a token belonging to the profile owner.')
    pages = api('user/repos', {'affiliation': 'owner', 'per_page': '100'}, paginate=True)
    if not isinstance(pages, list) or any(not isinstance(page, list) for page in pages):
        raise RuntimeError('Incomplete repository list; the previous card was kept.')
    repositories = []
    seen = set()
    for page in pages:
        for repo in page:
            if repo['owner']['login'].casefold() != username.casefold():
                continue
            # Copies of other projects and the profile's own generators are excluded.
            if repo['fork'] or repo['name'].casefold() == username.casefold():
                continue
            if repo['id'] not in seen:
                repositories.append(repo)
                seen.add(repo['id'])
    if not any(repo['private'] for repo in repositories):
        raise RuntimeError('No private repositories are visible. Check PROFILE_STATS_TOKEN access; the previous card was kept.')
    return [api(f"repos/{repo['full_name']}/languages") for repo in repositories]


def aggregate(repositories):
    totals = Counter()
    for languages in repositories:
        if not isinstance(languages, dict):
            raise ValueError('Invalid language response')
        for name, size in languages.items():
            if not isinstance(name, str) or not name or type(size) is not int or size < 0:
                raise ValueError('Invalid language data')
            if size:
                totals[name] += size
    if not totals:
        raise ValueError('No language data; the previous card was kept.')
    return dict(sorted(totals.items(), key=lambda item: (-item[1], item[0])))


def render(totals):
    total = sum(totals.values())
    rows = (len(totals) + 1) // 2
    # Each new language receives a label; the card grows instead of hiding entries.
    height = max(155, 113 + rows * 22)
    labels = [(name, count / total * 100) for name, count in totals.items()]
    description = ', '.join(f'{name}: {percent:.2f}%' for name, percent in labels)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="325" height="{height}" viewBox="0 0 325 {height}" role="img" aria-labelledby="title desc">',
             '<title id="title">Languages across public and private projects</title>',
             f'<desc id="desc">{escape(description)}. Share of code bytes reported by GitHub. Owned repositories only; forks and profile repository excluded.</desc>',
             '<style>text{font-family:Segoe UI,Ubuntu,sans-serif;fill:#fff}.heading{font-size:18px;font-weight:600;fill:#7fff00}.language{font-size:11px}.note{font-size:10px;fill:#9e9e9e}</style>',
             '<text x="25" y="35" class="heading">Most Used Languages</text>',
             '<defs><clipPath id="bar"><rect x="25" y="54" width="275" height="8" rx="4"/></clipPath></defs>',
             '<g clip-path="url(#bar)">']
    x = 25.0
    for name, percent in labels:
        width = 275 * percent / 100
        color = COLORS.get(name, '#9e9e9e')
        parts.append(f'<rect x="{x:.4f}" y="54" width="{width:.4f}" height="8" fill="{color}"/>')
        x += width
    parts.append('</g>')
    for i, (name, percent) in enumerate(labels):
        x, y = 25 + (i % 2) * 145, 84 + (i // 2) * 22
        display_percent = '<0.01%' if percent < .01 else f'{percent:.2f}%'
        # Separate percentage and language columns to keep long names legible.
        parts.extend([f'<circle cx="{x + 4}" cy="{y - 4}" r="4" fill="{COLORS.get(name, "#9e9e9e")}"/>',
                      f'<text x="{x + 13}" y="{y}" class="language">{escape(name)}</text>',
                      f'<text x="{x + 126}" y="{y + 12}" text-anchor="end" class="note">{escape(display_percent)}</text>'])
    parts.append(f'<text x="25" y="{height - 13}" class="note">Public + private projects · share of code bytes</text>')
    return '\n'.join(parts + ['</svg>', ''])


def publish(output, svg):
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(mode='w', dir=output.parent, encoding='utf-8', delete=False) as handle:
        temporary = Path(handle.name)
        handle.write(svg)
    temporary.replace(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='maxsampa')
    parser.add_argument('--output', type=Path, default=Path('assets/languages.svg'))
    args = parser.parse_args()
    totals = aggregate(fetch_languages(args.username))
    publish(args.output, render(totals))
    # Aggregate language names and percentages only; no private repository metadata.
    print(json.dumps({name: round(size / sum(totals.values()) * 100, 2) for name, size in totals.items()}))


if __name__ == '__main__':
    try:
        main()
    except (RuntimeError, ValueError, KeyError, subprocess.TimeoutExpired) as error:
        print(f'Language update failed: {error}', file=sys.stderr)
        sys.exit(1)
