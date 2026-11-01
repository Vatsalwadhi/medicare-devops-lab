#!/bin/bash
# Runtime DevSecOps evidence for MediCare+ (run on the EC2 host)
K="sudo k3s kubectl"
echo "===== 1. Secret scanning catches a leaked token (scratch dir, not the repo) ====="
D=$(mktemp -d); printf 'GITHUB_TOKEN = "ghp_%s"\n' "$(tr -dc 'A-Za-z0-9' </dev/urandom | head -c 36)" > $D/settings.py
trivy fs --scanners secret --exit-code 1 --quiet $D 2>/dev/null | grep -E "Total|CRITICAL|HIGH|GitHub" | head -4; echo "trivy exit code: ${PIPESTATUS[0]}"; rm -rf $D
echo; echo "===== 2. Pod Security Admission (restricted) blocks a privileged pod ====="
$K -n medicare run privtest --image=busybox:1.36 --restart=Never --privileged -- sleep 5 2>&1 | cut -c1-170
echo; echo "===== 3. NetworkPolicy: only web tier may reach PostgreSQL ====="
echo -n "from web pod      -> "; $K -n medicare exec deploy/medicare-web -- python -c "import socket;s=socket.create_connection(('postgres',5432),3);print('CONNECTED')" 2>&1 | tail -1
echo -n "from other ns pod -> "; $K run nettest -n default --rm -i --quiet --image=busybox:1.36 --restart=Never -- sh -c "nc -z -w 3 postgres.medicare.svc.cluster.local 5432 && echo CONNECTED || echo BLOCKED (timeout)" 2>&1 | tail -1
echo; echo "===== 4. PHI encrypted at rest (raw DB rows) ====="
$K -n medicare exec postgres-0 -- sh -c 'psql -U "$POSTGRES_USER" -d medicare -t -c "select id, left(diagnosis_enc,70) as diagnosis_enc from medical_records"' 2>&1 | head -3
echo; echo "===== 5. Security headers on live app ====="
curl -sI http://localhost:30080/ | grep -Ei "content-security|x-frame|x-content-type|referrer|cross-origin|permissions" 
echo; echo "===== 6. Workload hardening ====="
$K -n medicare get pods -o custom-columns='POD:.metadata.name,NONROOT:.spec.securityContext.runAsNonRoot,USER:.spec.securityContext.runAsUser,RO_ROOTFS:.spec.containers[0].securityContext.readOnlyRootFilesystem,PRIV_ESC:.spec.containers[0].securityContext.allowPrivilegeEscalation' | grep -v bg
$K get ns medicare -o jsonpath='{.metadata.labels}' | tr ',' '\n' | grep pod-security
