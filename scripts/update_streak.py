"""Generate a contribution card, preferring the latest streak on ties."""
import argparse
from datetime import date, datetime, timedelta
from html import escape
import json
from pathlib import Path
import subprocess
from zoneinfo import ZoneInfo


def graphql(query, **variables):
    args = ['gh', 'api', 'graphql', '-f', f'query={query}']
    for key, value in variables.items():
        args.extend(['-f', f'{key}={value}'])
    response = json.loads(subprocess.check_output(args, text=True, timeout=90))
    if response.get('errors'):
        raise RuntimeError(response['errors'])
    return response['data']['user']


def fetch_days(username, today):
    user = graphql('query($login:String!){user(login:$login){createdAt}}', login=username)
    created = date.fromisoformat(user['createdAt'][:10])
    days = {}
    query = '''query($login:String!,$from:DateTime!,$to:DateTime!){
      user(login:$login){contributionsCollection(from:$from,to:$to){
        contributionCalendar{weeks{contributionDays{date contributionCount}}}
      }}
    }'''
    for year in range(created.year, today.year + 1):
        end = min(date(year, 12, 31), today)
        user = graphql(query, login=username, **{
            'from': f'{year}-01-01T00:00:00Z', 'to': f'{end.isoformat()}T23:59:59Z'})
        for week in user['contributionsCollection']['contributionCalendar']['weeks']:
            for day in week['contributionDays']:
                when = date.fromisoformat(day['date'])
                if created <= when <= today:
                    days[when] = day['contributionCount']
    # Never overwrite a good card with an incomplete API response.
    expected = {created + timedelta(days=i) for i in range((today-created).days+1)}
    if set(days) != expected:
        raise RuntimeError('Incomplete contribution calendar')
    return days


def calculate(days, today):
    active = sorted(day for day, count in days.items() if count > 0 and day <= today)
    best = current = (0, None, None)
    previous = None
    for day in active:
        length, start, _ = current
        current = (length + 1, start, day) if previous == day - timedelta(days=1) else (1, day, day)
        # Chronological traversal means equal lengths replace older records.
        if current[0] >= best[0]:
            best = current
        previous = day
    if previous is None or previous < today - timedelta(days=1):
        current = (0, None, None)
    return {'total': sum(count for day, count in days.items() if day <= today),
            'first': active[0] if active else None, 'current': current, 'longest': best}


def format_date(day):
    return day.strftime('%b ') + str(day.day) + day.strftime(', %Y')


def date_range(start, end):
    if start is None:
        return 'No contributions yet'
    return format_date(start) if start == end else f'{format_date(start)} – {format_date(end)}'


def render(stats):
    current, longest = stats['current'], stats['longest']
    first = format_date(stats['first']) if stats['first'] else 'No contributions yet'
    columns = [(82, stats['total'], 'Total Contributions', f'{first} – Present'),
               (247, current[0], 'Current Streak', date_range(*current[1:])),
               (412, longest[0], 'Longest Streak', date_range(*longest[1:]))]
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" width="495" height="195" viewBox="0 0 495 195" role="img" aria-labelledby="title desc">',
             '<title id="title">GitHub contribution streak</title>',
             f'<desc id="desc">{stats["total"]} contributions. Current streak: {current[0]} days. Longest streak: {longest[0]} days, {escape(date_range(*longest[1:]))}. Most recent streak wins ties.</desc>',
             '<style>text{font-family:Segoe UI,Ubuntu,sans-serif;text-anchor:middle;fill:#fff}.label{font-size:14px;fill:#7fff00}.dates{font-size:10px;fill:#9e9e9e}.number{font-size:28px;font-weight:700}</style>',
             '<path d="M165 40v115 M330 40v115" stroke="#333"/>',
             '<circle cx="247" cy="72" r="38" fill="none" stroke="#7fff00" stroke-width="3"/>']
    for x, value, label, dates in columns:
        parts.extend([f'<text x="{x}" y="82" class="number">{value}</text>',
                      f'<text x="{x}" y="133" class="label">{label}</text>',
                      f'<text x="{x}" y="158" class="dates">{escape(dates)}</text>'])
    return '\n'.join(parts + ['</svg>', ''])


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--username', default='maxsampa')
    parser.add_argument('--output', type=Path, default=Path('assets/contribution-streak.svg'))
    args = parser.parse_args()
    today = datetime.now(ZoneInfo('America/Fortaleza')).date()
    stats = calculate(fetch_days(args.username, today), today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(render(stats), encoding='utf-8')
    print(json.dumps(stats, default=str))
