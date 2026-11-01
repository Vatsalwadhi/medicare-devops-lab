#!/bin/bash
# Headless Jenkins configuration for the MediCare+ DevOps lab
set -e
J=/var/lib/jenkins
D=$(cd "$(dirname "$0")" && pwd)
echo ">> Installing plugins"
curl -fsSL -o /tmp/jpm.jar https://github.com/jenkinsci/plugin-installation-manager-tool/releases/download/2.14.0/jenkins-plugin-manager-2.14.0.jar
sudo systemctl stop jenkins
sudo -u jenkins java -jar /tmp/jpm.jar --war /opt/jenkins/jenkins.war -d $J/plugins \
  --plugins workflow-aggregator git github timestamper junit pipeline-stage-view pipeline-graph-view ws-cleanup \
  2>&1 | tail -3
echo ">> Admin user and jobs"
sudo mkdir -p $J/init.groovy.d $J/secrets
[ -s $J/secrets/admin_pw ] || openssl rand -base64 18 | tr -d '/+=' | head -c 16 | sudo tee $J/secrets/admin_pw >/dev/null
sudo cp "$D/01-security.groovy" "$D/02-jobs.groovy" $J/init.groovy.d/
sudo chown -R jenkins:jenkins $J
sudo chmod 600 $J/secrets/admin_pw
grep -q runSetupWizard /etc/systemd/system/jenkins.service || \
  sudo sed -i 's#ExecStart=/usr/bin/java #ExecStart=/usr/bin/java -Djenkins.install.runSetupWizard=false #' /etc/systemd/system/jenkins.service
sudo systemctl daemon-reload
sudo systemctl start jenkins
for i in $(seq 1 60); do
  code=$(curl -s -o /dev/null -w '%{http_code}' http://localhost:8080/login || true)
  [ "$code" = "200" ] && break; sleep 5
done
echo "Jenkins HTTP status: $code"
sudo grep -h "MediCare lab" /var/log/syslog 2>/dev/null | tail -5 || true
sudo journalctl -u jenkins --no-pager | grep -E "MediCare lab|SEVERE" | tail -8
ls $J/plugins/*.jpi 2>/dev/null | wc -l | xargs echo "plugins installed:"
sudo ls $J/jobs
