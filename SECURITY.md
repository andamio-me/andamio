# Security policy

andamio hardens servers and runs other people's apps, so security reports are the most
important issues this project gets. Thank you for taking the time.

*Español: reporta vulnerabilidades en privado como se explica abajo, nunca en un issue público.*

## Reporting a vulnerability

**Do not open a public issue, discussion or pull request.**

Use GitHub's private reporting: **Security** tab → **Report a vulnerability**. Only the
maintainer sees it until a fix is published.

Please include:

- what an attacker can do, and from where (internet, VPN, an app container, a user on the server);
- steps to reproduce, and the andamio commit you tested;
- the provider and OS of the server, if relevant.

## What to expect

andamio is maintained by one person, so timelines are best effort:

- acknowledgement within 7 days;
- a fix or a mitigation plan within 30 days for anything that exposes a server or its data;
- credit in the release notes, unless you prefer to stay anonymous.

## Supported versions

andamio is in alpha: only the latest commit on `main` gets security fixes. Instances
created from the template should pull fixes from upstream.

## Scope

In scope: everything in this repository (Ansible roles, CLIs, stacks, CI workflows), and
insecure defaults, even when they are documented.

Out of scope: vulnerabilities in Traefik, Docker, WireGuard, PostgreSQL and other upstream
projects (report them upstream; tell us if andamio's configuration makes them worse), and
issues that need root on the server or the owner's age key.
