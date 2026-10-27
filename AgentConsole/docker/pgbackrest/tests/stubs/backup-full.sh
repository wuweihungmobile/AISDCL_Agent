#!/usr/bin/env bash
# docker/pgbackrest/tests/stubs/backup-full.sh — backup-full.sh 的測試替身（行為見 _stub_job_common.sh）
exec bash "$(dirname "${BASH_SOURCE[0]}")/_stub_job_common.sh" full "$@"
