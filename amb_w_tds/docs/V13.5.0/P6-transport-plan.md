# V13.5.0 P6 — Transport Plan

**Version:** 1.0
**Date:** 2026-04-22
**Author:** MiniMax Agent
**Status:** Draft — Pending Orchestrator G1

---

## 1. Overview

P6 is the production deployment phase for V13.5.0. Two stages: Stage A (test) and Stage B (prod). Each stage follows the same T0–T7 playbook. The observation window applies only between stages.

### Target Version
- **Final tag:** `v13.5.0` (non-rc) applied only after Stage B CERTIFIED by orchestrator (G6)

### Apps in Scope (5 total)
| App | P2 Branch | Target Commit |
|-----|-----------|---------------|
| amb_w_tds | `v13.5-p2-fixtures-amb_w_tds` | `6bd4f60` |
| amb_w_spc | `v13.5-p2-fixtures-amb_w_spc` | `1dfb1e8` |
| rnd_warehouse_management | `v13.5-p2-fixtures-rnd_warehouse_management` | `33a7e58` |
| raven_ai_agent | `v13.5-p2-fixtures-raven_ai_agent` | `5ff0a25` |
| erpnext_mexico_compliance | TBD | TBD |

**Note:** `rnd_warehouse_management` and `raven_ai_agent` have NO `origin/V13.5.0` branch. Their rollback anchor is the `pre-V13.5-P2-merge-20260421` tag.

---

## 2. Rollback Decision Tree

### Decision Criteria
| Condition | Action |
|-----------|--------|
| T4.2 commit mismatch | STOP — do not deploy |
| `bench update` non-zero exit | STOP — rollback decision tree |
| `bench migrate` shows errors | STOP — rollback decision tree |
| T5 health check failure | STOP — rollback decision tree |
| T6 smoke test failure | STOP — rollback decision tree |
| Docker unhealthy containers | STOP — rollback decision tree |

### Rollback Levels
1. **R1 — Git Tag Rollback:** Switch apps to `pre-V13.5-P2-merge-20260421` tag
2. **R2 — Kill-Patch Reversion:** Revert P3/P4 kill-patch commits
3. **R3 — DB Restore:** Restore from pre-deploy backup (S3)
4. **R4 — Full Rebuild + DNS Swap:** Last resort

---

## 3. Stage Targets

### Stage A — Test
| Parameter | Value |
|-----------|-------|
| Host | `187.77.2.74` |
| Container | `erpnext-test-backend-1` |
| Site | `test.sysmayal2.cloud` |
| S3 prefix | `s3://frappe-backups-prod-2026/audit/V13.5.0/P6/stageA/` |

### Stage B — Production
| Parameter | Value |
|-----------|-------|
| Host | `72.62.131.198` |
| Container | TBD (from `docker ps` on host) |
| Site | `erp.sysmayal2.cloud` |
| S3 prefix | `s3://frappe-backups-prod-2026/audit/V13.5.0/P6/stageB/` |
| **Maintenance Window** | Sunday 22:00–23:00 Mexico City / 03:00–04:00 UTC Monday |

---

## 4. Playbook T0–T7 (per stage)

### T0 — Transport Plan (this document)
- Create at `apps/amb_w_tds/docs/V13.5.0/P6-transport-plan.md`
- Commit on branch `v13.5-p6-transport-plan` → PR → wait for orchestrator G1

### T1 — Pre-flight
```bash
HOST=<target_host>
ssh root@$HOST "mkdir -p /home/frappe/archived/V13.5-P6/stage$STAGE"
ssh root@$HOST "date -u; df -h /; docker ps --format 'table {{.Names}}\t{{.Status}}' | tee /home/frappe/archived/V13.5-P6/stage$STAGE/00-preflight.txt"
ssh root@$HOST "docker exec $CONTAINER bash -lc 'cd /home/frappe/frappe-bench && bench version && bench --site $SITE list-apps'" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/01-bench-state-BEFORE.txt
```

### T2 — Pre-deploy Backup (GATE G2/G5)
```bash
ssh root@$HOST "/root/gitops/backup.sh" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/10-backup.log
BKID=$(ssh root@$HOST "ls -1tr /root/gitops/backups | tail -1")
ssh root@$HOST "cd /root/gitops/backups/$BKID && sha256sum * > checksums.sha256"
ssh root@$HOST "aws --profile frappe-backups s3 cp /root/gitops/backups/$BKID/ s3://.../audit/V13.5.0/P6/stage$STAGE-backup/$BKID/ --recursive"
```

### T3 — Tag Verification
```bash
for a in amb_w_tds amb_w_spc rnd_warehouse_management raven_ai_agent erpnext_mexico_compliance; do
  echo "=== $a ==="
  git ls-remote --tags git@github.com:rogerboy38/$a.git v13.5.0-rc1 \
    | tee -a /home/frappe/archived/V13.5-P6/stage$STAGE/20-remote-tags.txt
done
```

### T4 — Deployment Sequence
```bash
# 4.1 Fetch tags inside container
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc '
  cd /home/frappe/frappe-bench &&
  for a in amb_w_tds amb_w_spc rnd_warehouse_management raven_ai_agent erpnext_mexico_compliance; do
    git -C apps/\$a fetch --tags origin
  done
'" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/30-fetch-tags.log

# 4.2 Switch each app to P2 branch (V13.5.0 for amb_w_tds/amb_w_spc, P2 branch for others)
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc '
  cd /home/frappe/frappe-bench &&
  bench switch-to-branch v13.5-p2-fixtures-amb_w_tds amb_w_tds &&
  bench switch-to-branch v13.5-p2-fixtures-amb_w_spc amb_w_spc &&
  bench switch-to-branch v13.5-p2-fixtures-rnd_warehouse_management rnd_warehouse_management &&
  bench switch-to-branch v13.5-p2-fixtures-raven_ai_agent raven_ai_agent
'" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/31-switch-branches.log

# 4.3 bench update
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc '
  cd /home/frappe/frappe-bench &&
  bench update --pull --no-backup --reset --skip-assets 2>&1
'" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/40-bench-update.log

# 4.4 bench migrate
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc '
  cd /home/frappe/frappe-bench &&
  bench --site $SITE migrate 2>&1
'" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/41-bench-migrate.log

# 4.5 bench build
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc '
  cd /home/frappe/frappe-bench &&
  bench build 2>&1
'" 2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/42-bench-build.log

# 4.6 Restart services
ssh root@$HOST "docker compose -f <compose-file> restart backend frontend scheduler worker-short worker-long websocket" \
  2>&1 | tee /home/frappe/archived/V13.5-P6/stage$STAGE/43-restart.log
```

### T5 — Post-deploy Health Checks
```bash
# 5.1 App list & versions
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc 'cd /home/frappe/frappe-bench && bench --site $SITE list-apps && bench version'" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/50-bench-state-AFTER.txt

# 5.2 HTTP probe
curl -sSIk "https://$SITE" -o /dev/null -w "%{http_code} %{time_total}\n" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/51-http-probe.txt

# 5.3 Scheduler status
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc 'bench --site $SITE scheduler status'" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/52-scheduler.txt

# 5.4 Docker health
ssh root@$HOST "docker ps --filter status=unhealthy --filter status=restarting" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/53-docker-unhealthy.txt

# 5.5 Error log tail
ssh root@$HOST "docker exec $CONTAINER bash -lc 'tail -200 /home/frappe/frappe-bench/logs/web.error.log'" \
  | tee /home/frappe/archived/V13.5-P6/stage$STAGE/54-web-error-tail.log
```

### T6 — Functional Smoke Tests
Run against site: Chrome + Firefox login, perform trigger, capture screenshot + console log.
Forms: 10 key forms from P3/P4 checklist.

### T7 — Upload Artifacts
```bash
aws --profile frappe-backups s3 sync /home/frappe/archived/V13.5-P6/stage$STAGE/ \
  s3://frappe-backups-prod-2026/audit/V13.5.0/P6/stage$STAGE/ --delete
```

---

## 5. Hand-off & Observation

### T8 — Hand-off to Orchestrator (Stage A only)
Ping template:
> P6 Stage A complete on `<host>` / `<site>`.
> Backup ID: `<BKID>`, Migrate: clean, Build: clean, Health: all green, Smoke: 10/10.
> Artifacts: `s3://.../P6/stageA/`. Awaiting DeepSeek audit + G3 approval.

### T9 — Observation Window (Stage A only, post G3)
- Duration: 24–48 h
- Hourly: error log tail, scheduler status
- Daily: UAT session log
- Upload `observation-<date>.md` to S3

### T11 — Hand-off (Stage B)
Same template as T8, targeting prod host.

---

## 6. Final Tag & Monitoring

### T12 — Final v13.5.0 Tags (after G6 only)
```bash
for a in amb_w_tds amb_w_spc rnd_warehouse_management raven_ai_agent erpnext_mexico_compliance; do
  cd ~/frappe-bench/apps/$a
  git fetch origin
  git checkout V13.5.0 && git pull --ff-only
  git tag -a v13.5.0 -m "V13.5.0 final release — P6 deployed to prod on <date>"
  git push origin v13.5.0
done
```

### T13 — Post-deploy Monitoring (72 h)
- 5-min health probe: `curl -sSIk https://erp.sysmayal2.cloud`
- Daily backup validation (08:00 UTC)
- 6-hourly error budget snapshot
- Rolling logs to S3

### T14 — Rollback Playbooks (standby)

**R1 — Git Tag Rollback:**
```bash
for a in amb_w_tds amb_w_spc rnd_warehouse_management raven_ai_agent; do
  ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc 'cd /home/frappe/frappe-bench && git -C apps/\$a checkout pre-V13.5-P2-merge-20260421'"
done
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc 'cd /home/frappe/frappe-bench && bench update --pull --no-backup --reset && bench --site $SITE migrate && bench build'"
```

**R3 — DB Restore:**
```bash
BKID=<from T2>
ssh root@$HOST "docker exec -u frappe $CONTAINER bash -lc 'cd /home/frappe/frappe-bench && bench --site $SITE restore /mnt/s3-backups/$BKID/<sitename>-database.sql.gz --with-public-files /mnt/s3-backups/$BKID/<sitename>-files.tar --with-private-files /mnt/s3-backups/$BKID/<sitename>-private-files.tar'"
```

---

## 7. Hard Rules

1. Never deploy without fresh pre-deploy backup (G2/G5).
2. Never skip T4.2 git SHA verification — HEAD must match target commit.
3. Never merge PRs or push except final `v13.5.0` tag after G6.
4. Never deploy outside announced maintenance window.
5. Never run Stage B before Stage A observation complete + G4.
6. Never edit code inside target container.
7. Never run rollback without orchestrator authorization.
8. Never store backups only on local disk — must sync to S3 within 15 min.
9. Never suppress errors or delete logs during deployment.
10. Never start post-deploy monitoring before hand-off ping sent.
11. Never promote `v13.5.0-rc1` to `v13.5.0` before G6.
12. Stop within 60 seconds and report to orchestrator if any stop condition fires.

---

## 8. Deliverables

- [ ] `P6-transport-plan.md` committed + PR
- [ ] Stage A artifact bundle → S3
- [ ] Observation window completed
- [ ] Stage B artifact bundle → S3
- [ ] Post-deploy monitoring logs (72 h)
- [ ] Final `v13.5.0` tags on all 5 apps
- [ ] `V13.5-P6-COMPLETE.md` committed + PR
- [ ] Master manifest on S3
