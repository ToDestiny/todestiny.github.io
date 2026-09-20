# Elysian Wars external public availability watch

This candidate checks the public website and API readiness from standard
GitHub-hosted Ubuntu runners, outside the application VPS and the operator's
Mac. It is **not activated by adding its files**: the exact repository/default
branch/public-repository guards and `EW_PUBLIC_MONITOR_ENABLED=true` repository
variable must also match.

## Scope and behavior

Every 15 minutes, at minutes 7, 22, 37 and 52 UTC, the workflow checks exactly:

- `https://www.elysianwars.com/`: verified TLS, HTTP 200, HTML content type.
- `https://www.elysianwars.com/api/health/ready`: verified TLS, HTTP 200, JSON
  content type and the exact successful values `status=ready`, `database=ready`.

It takes two samples 10 seconds apart. Both failing samples open one incident;
repeated failures leave the same incident quiet. Two healthy samples close an
existing incident with a recovery comment. Mixed samples are explicitly
`unconfirmed_failure` and neither open nor close an incident. Failure means a
public probe failed, not proof of a specific root cause. A successful workflow
conclusion means the monitor/notification operation completed; the run summary
and incident show the site's availability state.

Incident creation assigns and mentions **@ToDestiny**. Recovery mentions the same
owner. Only incidents created by `github-actions[bot]` with the exact marker and
title are changed. Notification drills use a separate marker/title and cannot
close a real incident. There is no VPS repair, restart, login, account creation,
private API, production saved-state write, email credential or application token.
Bodies go to `/dev/null`, except bounded readiness JSON which is interpreted and
discarded; public incident text contains only fixed reason codes and HTTP statuses.

## Existing execution surface and permissions

The candidate is bound to the already-owned public repository
`ToDestiny/todestiny.github.io`, default branch `main`. That repository's existing
Actions and Issues capabilities were available during preparation. It has
**GitHub Pages enabled**: publishing the monitoring files to its default branch
may also trigger its existing Pages publication. The coordinating owner must
review that side effect before selecting this execution surface. No existing
site file is part of the candidate.

The private `ToDestiny/ElysianWars` repository is deliberately refused by the
workflow and notifier. A frequent private-repository workflow consumes the
account's shared included minutes and may become billable. Standard hosted
runners on a public repository are free under GitHub's current policy. The
candidate uses no larger runner, artifact upload, cache, new VPS or purchased
service. [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions).

The automatic short-lived `GITHUB_TOKEN` receives only `contents: read` for the
pinned checkout and `issues: write` for owner notification. Checkout does not
persist credentials. The token is passed only to the notification step, never
to the public probes. GitHub API redirects are rejected so that the token cannot
follow a response to another host. No repository secret needs to be created.

## Activation after owner review

1. In an isolated checkout of the selected public repository, recheck its
   owner, visibility, default branch, Actions permission, existing Pages behavior
   and the absence of collisions in the four candidate paths. If a different
   public repository is selected, review the corresponding exact repository
   binding in both the workflow and Python script before publishing. Never make
   the Elysian Wars source repository public to activate this monitor.
2. Run the offline tests below, review the exact diff and publish only the four
   monitoring candidate files through the repository's normal review process.
   Existing application/VPS deployment workflows are not part of this candidate.
3. As **ToDestiny**, enable GitHub Actions failure notifications and participating/
   mention notifications in the desired GitHub/email channels. An issue assignment
   or mention requests a notification; it does not prove inbox delivery. GitHub
   notification preferences can suppress email. [Notification settings](https://docs.github.com/en/subscriptions-and-notifications/get-started/configuring-notifications),
   [workflow notifications](https://docs.github.com/en/actions/concepts/workflows-and-actions/notifications-for-workflow-runs).
4. Explicitly enable and dispatch the workflow after reviewing the notification
   destination. These commands change GitHub settings and run the monitor:

   ```sh
   gh variable set EW_PUBLIC_MONITOR_ENABLED --body true --repo ToDestiny/todestiny.github.io
   gh workflow enable elysianwars-public-availability.yml --repo ToDestiny/todestiny.github.io
   gh workflow run elysianwars-public-availability.yml --repo ToDestiny/todestiny.github.io --ref main -f mode=observe
   ```

5. Verify both real probes and the workflow summary. Then run the clearly marked
   owner-notification drill; it does **not** interrupt the website:

   ```sh
   gh workflow run elysianwars-public-availability.yml --repo ToDestiny/todestiny.github.io --ref main -f mode=drill_down
   ```

   Confirm the new drill issue is assigned to `ToDestiny`, and independently
   confirm the owner's actual GitHub notification or configured email receipt.
   Repeat the same drill once and verify that it creates no second issue/comment.
   Only then run `mode=drill_recovery` and verify the recovery notification and
   closure. Retain the run/issue links and actual delivery result.
6. Observe at least one real scheduled run from GitHub's hosted runner. Mark
   installation, public checking, scheduled operation and owner delivery as
   separate evidence claims. Until this is done, this remains an implemented,
   locally tested candidate, not an active or notification-verified monitor.

## Stop and rollback

Disable the exact workflow to stop both probes and notifications; retained
incidents and previous run evidence are preserved:

```sh
gh workflow disable elysianwars-public-availability.yml --repo ToDestiny/todestiny.github.io
gh variable set EW_PUBLIC_MONITOR_ENABLED --body false --repo ToDestiny/todestiny.github.io
```

If code rollback is needed, revert only the monitoring change after review.
Do not remove unrelated workflows/site files or delete incident evidence. Close
any open drill explicitly when appropriate; do not label a disabled real outage
as recovered. Re-enable only after the same activation/delivery checks.

## Reliability boundaries

GitHub schedules run from the default branch, can be delayed or dropped during
load, and public-repository schedules can be disabled after 60 days without
repository activity. Schedule changes or re-enabling can also change who receives
native Actions notifications. This design therefore offers useful external
outage detection on existing resources, **not a guaranteed 15-minute alert,
24/7 SLA or independent watchdog of GitHub itself**. The owner must check run
freshness and GitHub notifications regularly and revalidate after schedule,
repository visibility, ownership or notification-setting changes. It does not
create artificial keepalive commits. [Scheduled workflow limits](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

A GitHub/runner outage, repository suspension, missing schedule, notification
suppression or API permission failure can prevent an alert. Workflow failures
surface as failed runs; native Actions notifications are a secondary path only
when the owner enables them. This does not prove authenticated HQ behavior,
private saved-state preservation, backup/restore integrity or full shared-server
recovery. No Agency service is monitored.

## Local verification

```sh
python3 -I -B scripts/monitoring/test_elysianwars_public_watch.py
```

The offline suite exercises transport/TLS/status failure, readiness false
positives, body redaction, debounce, incident deduplication, owner assignment,
recovery, spoofed issues, private-repository refusal, partial scans, permission
failures and separate drill handling. It does not use the network or send a
notification. A parsed YAML file and a passing test suite do not attest GitHub
runner execution or inbox delivery.
