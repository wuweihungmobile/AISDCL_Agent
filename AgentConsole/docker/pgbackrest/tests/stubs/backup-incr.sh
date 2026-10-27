#!/usr/bin/env bash
# docker/pgbackrest/tests/stubs/backup-incr.sh — backup-incr.sh（差異備份）的測試替身（行為見 _stub_job_common.sh）
exec bash "$(dirname "${BASH_SOURCE[0]}")/_stub_job_common.sh" diff "$@"
