#!/usr/bin/env bash
# docker/pgbackrest/tests/stubs/pg_dump-offsite.sh — pg_dump-offsite.sh 的測試替身（行為見 _stub_job_common.sh）
exec bash "$(dirname "${BASH_SOURCE[0]}")/_stub_job_common.sh" dump "$@"
