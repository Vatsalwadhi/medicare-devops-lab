#!/usr/bin/env bash
# Blue-green deployment controller for MediCare+
#   bluegreen.sh deploy <image> <version>   -> deploy to idle colour, test it, switch traffic
#   bluegreen.sh rollback                     -> point live traffic back to the previous colour
#   bluegreen.sh status
set -euo pipefail
NS=medicare
DIR=$(cd "$(dirname "$0")/.." && pwd)
active() { kubectl -n $NS get svc medicare-live -o jsonpath='{.spec.selector.color}' 2>/dev/null || echo none; }
other()  { [ "$1" = "blue" ] && echo green || echo blue; }
switch_live() {
  kubectl -n $NS patch svc medicare-live -p "{\"metadata\":{\"annotations\":{\"bluegreen/active\":\"$1\"}},\"spec\":{\"selector\":{\"app\":\"medicare-bg\",\"color\":\"$1\"}}}"
  kubectl -n $NS patch svc medicare-preview -p "{\"spec\":{\"selector\":{\"app\":\"medicare-bg\",\"color\":\"$(other "$1")\"}}}"
}
smoke() {  # $1 = service name; checks health and reports the version served
  local ip; ip=$(kubectl -n $NS get svc "$1" -o jsonpath='{.spec.clusterIP}')
  for i in $(seq 1 20); do
    if curl -fsS --max-time 5 "http://$ip/api/health" >/dev/null 2>&1; then curl -fsS --max-time 5 "http://$ip/api/version"; echo; return 0; fi
    sleep 3
  done
  echo "Smoke test FAILED for $1"; return 1
}
status() {
  echo "Live colour: $(active)"
  kubectl -n $NS get deploy -l app=medicare-bg -o custom-columns=NAME:.metadata.name,READY:.status.readyReplicas,IMAGE:.spec.template.spec.containers[0].image
}
case "${1:-status}" in
  deploy)
    IMAGE=$2; VERSION=$3
    kubectl -n $NS get svc medicare-live >/dev/null 2>&1 || kubectl apply -f "$DIR/k8s/bluegreen/services.yaml"
    LIVE=$(active)
    if kubectl -n $NS get deploy "medicare-$LIVE" >/dev/null 2>&1; then TARGET=$(other "$LIVE"); else TARGET=$LIVE; fi
    echo ">>> Live colour is '$LIVE'; deploying $IMAGE ($VERSION) to idle colour '$TARGET'"
    sed -e "s#__COLOR__#$TARGET#g" -e "s#__IMAGE__#$IMAGE#g" -e "s#__VERSION__#$VERSION#g" \
      "$DIR/k8s/bluegreen/deployment.tmpl.yaml" | kubectl apply -f -
    kubectl -n $NS rollout status deploy/"medicare-$TARGET" --timeout=180s
    echo ">>> Testing '$TARGET' before it receives traffic"
    kubectl -n $NS patch svc medicare-preview -p "{\"spec\":{\"selector\":{\"app\":\"medicare-bg\",\"color\":\"$TARGET\"}}}"
    smoke medicare-preview
    echo ">>> Switching live traffic: $LIVE -> $TARGET"
    switch_live "$TARGET"
    smoke medicare-live
    status ;;
  rollback)
    LIVE=$(active); PREV=$(other "$LIVE")
    kubectl -n $NS get deploy "medicare-$PREV" >/dev/null || { echo "No previous colour to roll back to"; exit 1; }
    echo ">>> Rolling back live traffic: $LIVE -> $PREV"
    switch_live "$PREV"
    smoke medicare-live
    status ;;
  status) status ;;
esac
