#!/usr/bin/env python3
"""Anonymous public availability probes and deduplicated GitHub owner alerts.

No VPS credentials, application accounts, private bodies, repair or deploy actions.
Notification mode is separately invoked only by the explicitly enabled workflow.
"""
import argparse
import datetime as dt
import json
import os
from pathlib import Path
import re
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

REPOSITORY = 'ToDestiny/todestiny.github.io'
OWNER = 'ToDestiny'
CHECKS = (('website', 'https://www.elysianwars.com/'),
          ('api_readiness', 'https://www.elysianwars.com/api/health/ready'))
SCHEMA = 'ew-public-availability-v1'
MARKERS = {False: '<!-- ew-public-watch:v1:incident -->',
           True: '<!-- ew-public-watch:v1:drill -->'}
TITLES = {False: '[Elysian Wars] Public availability incident',
          True: '[Elysian Wars] External notification drill'}
REASONS = {'ok', 'http_status', 'tls_or_transport', 'response_too_large',
           'readiness_not_ready', 'invalid_readiness', 'unexpected_content_type',
           'probe_runtime_error', 'notification_drill'}


def utc():
    return dt.datetime.now(dt.timezone.utc).isoformat()


def probe(name, url):
    # No -L: a redirect is a failure, never a request to an unapproved target.
    readiness = name == 'api_readiness'
    args = ['/usr/bin/curl', '--disable', '--silent', '--noproxy', '*',
            '--proto', '=https', '--request', 'GET', '--connect-timeout', '5',
            '--max-time', '10', '--max-redirs', '0', '--max-filesize',
            '4096' if readiness else '2097152', '--output', '-' if readiness else '/dev/null',
            '--write-out', '\nEW_WATCH_META\n%{http_code}\n%{ssl_verify_result}\n%{content_type}\n', url]
    result = {'check': name, 'url': url, 'ok': False, 'http_status': None,
              'reason': 'probe_runtime_error'}
    try:
        # Output is bounded by curl's response-size cap; website body goes to /dev/null.
        run = subprocess.run(args, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                             stderr=subprocess.DEVNULL, timeout=12,
                             env={'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C'})
        if run.returncode:
            result['reason'] = 'response_too_large' if run.returncode == 63 else 'tls_or_transport'
            return result
        if len(run.stdout) > 8192:
            result['reason'] = 'response_too_large'
            return result
        body, meta = run.stdout.rsplit(b'\nEW_WATCH_META\n', 1)
        fields = meta.decode('ascii').splitlines()
        if len(fields) != 3 or not re.fullmatch(r'[1-5][0-9]{2}', fields[0]) or fields[1] != '0':
            result['reason'] = 'tls_or_transport'
            return result
        result['http_status'] = int(fields[0])
        if result['http_status'] != 200:
            result['reason'] = 'http_status'
            return result
        content_type = fields[2].split(';', 1)[0].strip().lower()
        if content_type != ('application/json' if readiness else 'text/html'):
            result['reason'] = 'unexpected_content_type'
            return result
        if readiness:
            try:
                data = json.loads(body)
                if not isinstance(data, dict):
                    raise ValueError()
            except (ValueError, UnicodeError):
                result['reason'] = 'invalid_readiness'
                return result
            if data.get('status') != 'ready' or data.get('database') != 'ready':
                result['reason'] = 'readiness_not_ready'
                return result
        result.update(ok=True, reason='ok')
    except (OSError, ValueError, UnicodeError, subprocess.TimeoutExpired):
        pass
    return result


def collect(probe_fn=probe, sleeper=time.sleep):
    samples = []
    for i in range(2):
        samples.append({'at': utc(), 'checks': [probe_fn(name, url) for name, url in CHECKS]})
        if i == 0:
            sleeper(10)
    successes = [all(row['ok'] for row in sample['checks']) for sample in samples]
    state = 'healthy' if all(successes) else 'outage' if not any(successes) else 'unconfirmed_failure'
    return {'schema': SCHEMA, 'state': state, 'samples': samples,
            'scope': 'Two anonymous public HTTPS observations; no private bodies or account access.'}


def validate_report(value):
    if not isinstance(value, dict) or value.get('schema') != SCHEMA or value.get('state') not in ('healthy', 'outage', 'unconfirmed_failure'):
        raise ValueError('invalid-report')
    if not isinstance(value.get('samples'), list) or len(value['samples']) != 2:
        raise ValueError('invalid-samples')
    successes = []
    for sample in value['samples']:
        if not isinstance(sample, dict) or not isinstance(sample.get('checks'), list) or len(sample['checks']) != 2:
            raise ValueError('invalid-checks')
        for row, (name, url) in zip(sample['checks'], CHECKS):
            if row.get('check') != name or row.get('url') != url or type(row.get('ok')) is not bool or row.get('reason') not in REASONS:
                raise ValueError('invalid-check')
            if row.get('http_status') is not None and (type(row['http_status']) is not int or not 100 <= row['http_status'] <= 599):
                raise ValueError('invalid-http-status')
            if row['ok'] != (row['reason'] == 'ok' and row['http_status'] == 200):
                raise ValueError('inconsistent-check')
        successes.append(all(row['ok'] for row in sample['checks']))
    expected = 'healthy' if all(successes) else 'outage' if not any(successes) else 'unconfirmed_failure'
    if value['state'] != expected:
        raise ValueError('inconsistent-state')
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


class GitHub:
    def __init__(self, token):
        self.token = token
        self.opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
            urllib.request.HTTPSHandler(context=ssl.create_default_context()), NoRedirect())

    def call(self, method, path, data=None):
        if not (path == '/repos/' + REPOSITORY or path.startswith('/repos/' + REPOSITORY + '/')) or not re.fullmatch(r'/[A-Za-z0-9_./?=&%+\[\]-]+', path):
            raise ValueError('api-path-refused')
        encoded = None if data is None else json.dumps(data).encode()
        request = urllib.request.Request('https://api.github.com' + path, data=encoded, method=method,
            headers={'Authorization': 'Bearer ' + self.token, 'Accept': 'application/vnd.github+json',
                     'Content-Type': 'application/json', 'X-GitHub-Api-Version': '2022-11-28',
                     'User-Agent': 'ElysianWars-public-watch'})
        try:
            with self.opener.open(request, timeout=15) as response:
                raw = response.read(524289)
            if len(raw) > 524288:
                raise ValueError('github-response-bound')
            return json.loads(raw)
        except urllib.error.HTTPError as exc:
            # Never log the body, URL parameters, request headers or token.
            raise RuntimeError('github-http-' + str(exc.code)) from None
        except (urllib.error.URLError, OSError):
            raise RuntimeError('github-transport-failed') from None


def open_incident(api, drill):
    matches = []
    for page in range(1, 4):
        rows = api.call('GET', '/repos/' + REPOSITORY + '/issues?state=open&creator=github-actions%5Bbot%5D&per_page=100&page=' + str(page))
        if not isinstance(rows, list):
            raise ValueError('invalid-issue-list')
        for row in rows:
            if (not isinstance(row, dict) or 'pull_request' in row or row.get('state') != 'open'
                    or row.get('user', {}).get('login') != 'github-actions[bot]'
                    or row.get('title') != TITLES[drill]
                    or not isinstance(row.get('body'), str) or not row['body'].startswith(MARKERS[drill] + '\n')):
                continue
            number = row.get('number')
            if type(number) is not int or number <= 0:
                raise ValueError('invalid-issue-number')
            matches.append(number)
        if len(rows) < 100:
            break
    else:
        raise ValueError('issue-pagination-incomplete')
    if len(matches) > 1:
        raise ValueError('multiple-owned-incidents-require-review')
    return matches[0] if matches else None


def render(report, run_url, drill, recovery=False):
    heading = 'Notification drill: ' if drill else ''
    heading += 'public checks recovered' if recovery else 'public availability check failed twice'
    lines = [MARKERS[drill], '', '@' + OWNER + ' — ' + heading + '.', '', '[Workflow evidence](' + run_url + ').', '']
    if drill:
        lines += ['This is an operator-requested notification test, not an observed production outage.', '']
    else:
        for i, sample in enumerate(report['samples'], 1):
            for row in sample['checks']:
                code = 'unavailable' if row['http_status'] is None else str(row['http_status'])
                lines.append(f"- Probe {i}, {row['check']}: HTTP {code}; {row['reason']}.")
        lines.append('')
    lines += ['Only public website/API readiness was checked. No private response body, credentials, account data or automated repair is included.',
              'GitHub scheduling can be delayed or disabled; this is an external probe, not a 24/7 availability guarantee.']
    return '\n'.join(lines)


def notify(api, report, mode, run_url):
    validate_report(report)
    repo = api.call('GET', '/repos/' + REPOSITORY)
    if (repo.get('full_name') != REPOSITORY or repo.get('private') is not False
            or repo.get('fork') is not False or repo.get('has_issues') is not True
            or repo.get('owner', {}).get('login') != OWNER):
        raise ValueError('public-owned-repository-required')
    drill = mode != 'observe'
    incident = open_incident(api, drill)
    state = 'outage' if mode == 'drill_down' else 'healthy' if mode == 'drill_recovery' else report['state']
    if state == 'outage' and incident is None:
        value = api.call('POST', '/repos/' + REPOSITORY + '/issues', {
            'title': TITLES[drill], 'body': render(report, run_url, drill), 'assignees': [OWNER]})
        if type(value.get('number')) is not int:
            raise ValueError('issue-create-unverified')
        return {'action': 'incident-opened', 'issue': value['number'], 'drill': drill}
    if state == 'healthy' and incident is not None:
        base = '/repos/' + REPOSITORY + '/issues/' + str(incident)
        # Comment before closure: a failed comment cannot silently erase an incident.
        api.call('POST', base + '/comments', {'body': render(report, run_url, drill, recovery=True)})
        api.call('PATCH', base, {'state': 'closed', 'state_reason': 'completed'})
        return {'action': 'recovery-notified-and-closed', 'issue': incident, 'drill': drill}
    return {'action': 'unchanged', 'state': state, 'issue': incident, 'drill': drill}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=('check', 'notify'))
    parser.add_argument('--result', type=Path, required=True)
    parser.add_argument('--mode', choices=('observe', 'drill_down', 'drill_recovery'), default='observe')
    args = parser.parse_args()
    if args.command == 'check':
        result = collect()
        args.result.write_text(json.dumps(result, indent=2) + '\n')
        print(json.dumps({'state': result['state'], 'private_bodies_returned': False}))
        return 0  # An outage is a successful observation; the next step opens an incident.
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != REPOSITORY:
        raise ValueError('enabled-github-workflow-required')
    if args.mode != 'observe' and os.environ.get('GITHUB_EVENT_NAME') != 'workflow_dispatch':
        raise ValueError('drill-requires-manual-dispatch')
    run_id = os.environ.get('GITHUB_RUN_ID', '')
    token = os.environ.get('GH_TOKEN', '')
    if not run_id.isdigit() or not token:
        raise ValueError('workflow-token-and-run-required')
    if args.result.stat().st_size > 16384:
        raise ValueError('report-size-bound')
    report = validate_report(json.loads(args.result.read_text()))
    run_url = 'https://github.com/' + REPOSITORY + '/actions/runs/' + run_id
    result = notify(GitHub(token), report, args.mode, run_url)
    print(json.dumps(result))
    summary = os.environ.get('GITHUB_STEP_SUMMARY')
    if summary:
        Path(summary).write_text('Elysian Wars public availability: **' + report['state'] + '**\n\n'
            + 'Notification action: `' + result['action'] + '`. A successful job means the observation/notification logic completed; consult the availability state.\n')
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        # Fail the workflow so native Actions failure notification can surface monitor failures.
        print('External monitor failed; no raw exception, private body or credential is emitted.', file=sys.stderr)
        sys.exit(1)
