#!/usr/bin/env python3
"""Offline failure, privacy and incident-transition tests; never sends requests."""
import importlib.util
import json
from pathlib import Path
import subprocess
import types
import unittest
from unittest.mock import patch

FILE = Path(__file__).with_name('elysianwars_public_watch.py')
spec = importlib.util.spec_from_file_location('watch', FILE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def response(body=b'', status='200', tls='0', content_type='text/html', exit_code=0):
    return types.SimpleNamespace(returncode=exit_code, stdout=body + b'\nEW_WATCH_META\n' +
        (status + '\n' + tls + '\n' + content_type + '\n').encode())


def report(healthy=True):
    return w.collect(lambda name, url: {'check': name, 'url': url, 'ok': healthy,
        'http_status': 200 if healthy else 503, 'reason': 'ok' if healthy else 'http_status'}, lambda _: None)


class FakeAPI:
    def __init__(self, issues=None, private=False, issue_failure=False):
        self.calls = []
        self.issues = issues or []
        self.private = private
        self.issue_failure = issue_failure

    def call(self, method, path, data=None):
        self.calls.append((method, path, data))
        if path == '/repos/' + w.REPOSITORY:
            return {'full_name': w.REPOSITORY, 'private': self.private, 'fork': False,
                    'has_issues': True, 'owner': {'login': w.OWNER}}
        if method == 'GET':
            return self.issues
        if self.issue_failure:
            raise RuntimeError('github-http-403')
        return {'number': 42}


def issue(drill=False, user='github-actions[bot]', number=41):
    return {'number': number, 'state': 'open', 'title': w.TITLES[drill],
            'body': w.MARKERS[drill] + '\nretained incident', 'user': {'login': user}}


class Probes(unittest.TestCase):
    def test_public_website_success(self):
        with patch.object(w.subprocess, 'run', return_value=response()) as run:
            actual = w.probe(*w.CHECKS[0])
        self.assertTrue(actual['ok'])
        args = run.call_args.args[0]
        self.assertEqual(args[:2], ['/usr/bin/curl', '--disable'])
        self.assertNotIn('-L', args)
        self.assertNotIn('--insecure', args)
        self.assertEqual(args[-1], w.CHECKS[0][1])
        self.assertEqual(run.call_args.kwargs['env'], {'PATH': '/usr/bin:/bin', 'LC_ALL': 'C', 'LANG': 'C'})

    def test_readiness_success_private_extra_fields_are_dropped(self):
        with patch.object(w.subprocess, 'run', return_value=response(
                b'{"status":"ready","database":"ready","secret":"PRIVATE"}', content_type='application/json; charset=utf-8')):
            actual = w.probe(*w.CHECKS[1])
        self.assertTrue(actual['ok'])
        self.assertNotIn('PRIVATE', json.dumps(actual))
        self.assertNotIn('secret', json.dumps(actual))

    def test_status_tls_transport_and_size_fail_closed(self):
        for value, reason in [(response(status='503'), 'http_status'),
                              (response(status='302'), 'http_status'),
                              (response(tls='20'), 'tls_or_transport'),
                              (response(exit_code=60), 'tls_or_transport'),
                              (response(exit_code=28), 'tls_or_transport'),
                              (response(exit_code=63), 'response_too_large'),
                              (response(b'x' * 9000), 'response_too_large')]:
            with self.subTest(reason=reason), patch.object(w.subprocess, 'run', return_value=value):
                actual = w.probe(*w.CHECKS[0])
                self.assertFalse(actual['ok'])
                self.assertEqual(actual['reason'], reason)

    def test_readiness_contract_not_merely_http200(self):
        for body, reason in [(b'{"status":"not_ready","database":"unavailable"}', 'readiness_not_ready'),
                             (b'[]', 'invalid_readiness'), (b'PRIVATE_INVALID_JSON', 'invalid_readiness'),
                             (b'{"status":"ready"}', 'readiness_not_ready')]:
            with self.subTest(body=body), patch.object(w.subprocess, 'run', return_value=response(body, content_type='application/json')):
                actual = w.probe(*w.CHECKS[1])
                self.assertEqual(actual['reason'], reason)
                self.assertNotIn('PRIVATE', json.dumps(actual))

    def test_content_type_mismatch(self):
        with patch.object(w.subprocess, 'run', return_value=response(content_type='application/json')):
            self.assertEqual(w.probe(*w.CHECKS[0])['reason'], 'unexpected_content_type')

    def test_runtime_exception_suppresses_message(self):
        with patch.object(w.subprocess, 'run', side_effect=OSError('PRIVATE_EXCEPTION')):
            self.assertNotIn('PRIVATE_EXCEPTION', json.dumps(w.probe(*w.CHECKS[0])))

    def test_debounce_transient_does_not_confirm_outage_or_recovery(self):
        index = 0
        def fake(name, url):
            nonlocal index
            index += 1
            ok = index > 2
            return {'check': name, 'url': url, 'ok': ok, 'http_status': 200 if ok else 503,
                    'reason': 'ok' if ok else 'http_status'}
        self.assertEqual(w.collect(fake, lambda _: None)['state'], 'unconfirmed_failure')
        self.assertEqual(report(False)['state'], 'outage')
        self.assertEqual(report(True)['state'], 'healthy')

    def test_report_rejects_destination_or_state_tampering(self):
        value = report()
        value['samples'][0]['checks'][0]['url'] = 'https://private.example/'
        with self.assertRaises(ValueError):
            w.validate_report(value)
        value = report(False)
        value['state'] = 'healthy'
        with self.assertRaises(ValueError):
            w.validate_report(value)


class Notifications(unittest.TestCase):
    def test_first_outage_creates_owner_assigned_mention(self):
        api = FakeAPI()
        out = w.notify(api, report(False), 'observe', 'https://github.com/owner/repo/actions/runs/1')
        self.assertEqual(out['action'], 'incident-opened')
        writes = [c for c in api.calls if c[0] != 'GET']
        self.assertEqual(len(writes), 1)
        self.assertEqual(writes[0][2]['assignees'], ['ToDestiny'])
        self.assertIn('@ToDestiny', writes[0][2]['body'])

    def test_repeat_outage_does_not_send_again(self):
        api = FakeAPI([issue()])
        self.assertEqual(w.notify(api, report(False), 'observe', 'https://github.com/a/b')['action'], 'unchanged')
        self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_recovery_notifies_then_closes_only_owned_incident(self):
        api = FakeAPI([issue()])
        out = w.notify(api, report(), 'observe', 'https://github.com/a/b')
        self.assertEqual(out['action'], 'recovery-notified-and-closed')
        writes = [c for c in api.calls if c[0] != 'GET']
        self.assertEqual([c[0] for c in writes], ['POST', 'PATCH'])
        self.assertTrue(writes[0][1].endswith('/41/comments'))
        self.assertEqual(writes[1][2]['state'], 'closed')

    def test_human_spoofed_issue_is_never_changed(self):
        api = FakeAPI([issue(user='someone-else')])
        out = w.notify(api, report(), 'observe', 'https://github.com/a/b')
        self.assertEqual(out['action'], 'unchanged')
        self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_private_repository_cannot_activate(self):
        api = FakeAPI(private=True)
        with self.assertRaises(ValueError):
            w.notify(api, report(False), 'observe', 'https://github.com/a/b')
        self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_transient_does_not_close_open_incident(self):
        value = report(False)
        for row in value['samples'][1]['checks']:
            row.update(ok=True, http_status=200, reason='ok')
        value['state'] = 'unconfirmed_failure'
        api = FakeAPI([issue()])
        self.assertEqual(w.notify(api, value, 'observe', 'https://github.com/a/b')['action'], 'unchanged')
        self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_drill_never_closes_real_incident(self):
        api = FakeAPI([issue()])
        out = w.notify(api, report(), 'drill_recovery', 'https://github.com/a/b')
        self.assertEqual(out['action'], 'unchanged')
        self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_drill_is_explicit_and_separate(self):
        api = FakeAPI()
        out = w.notify(api, report(), 'drill_down', 'https://github.com/a/b')
        self.assertTrue(out['drill'])
        write = next(c for c in api.calls if c[0] == 'POST')
        self.assertIn('not an observed production outage', write[2]['body'])
        self.assertEqual(write[2]['title'], w.TITLES[True])

    def test_multiple_incidents_or_incomplete_scan_fail_before_writes(self):
        for rows in ([issue(number=41), issue(number=42)], [issue(user='someone-else')] * 100):
            api = FakeAPI(rows)
            with self.assertRaises(ValueError):
                w.notify(api, report(False), 'observe', 'https://github.com/a/b')
            self.assertFalse(any(c[0] != 'GET' for c in api.calls))

    def test_permission_failure_is_not_reported_as_sent(self):
        with self.assertRaises(RuntimeError):
            w.notify(FakeAPI(issue_failure=True), report(False), 'observe', 'https://github.com/a/b')

    def test_recovery_comment_failure_does_not_close_incident(self):
        api = FakeAPI([issue()], issue_failure=True)
        with self.assertRaises(RuntimeError):
            w.notify(api, report(), 'observe', 'https://github.com/a/b')
        self.assertFalse(any(c[0] == 'PATCH' for c in api.calls))

    def test_github_token_cannot_follow_redirect_or_reach_other_repo(self):
        self.assertIsNone(w.NoRedirect().redirect_request(None, None, 302, None, None, 'https://other.example/'))
        client = w.GitHub('PRIVATE_TOKEN')
        with self.assertRaises(ValueError):
            client.call('GET', '/repos/' + w.REPOSITORY + '-other')


if __name__ == '__main__':
    unittest.main()
