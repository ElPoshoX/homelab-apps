#!/usr/bin/env bash
set -euo pipefail

GRAFANA_URL="${GRAFANA_URL:-https://grafana.elposhox.dev}"
DASHBOARD_UID="adqvb4t"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
JSON_FILE="${SCRIPT_DIR}/dashboards/claude-code.json"
CM_FILE="${SCRIPT_DIR}/dashboard-claude-code-cm.yaml"

if [[ -z "${GRAFANA_USER:-}" || -z "${GRAFANA_PASS:-}" ]]; then
  echo "Set GRAFANA_USER and GRAFANA_PASS env vars"
  exit 1
fi

echo "Exporting dashboard ${DASHBOARD_UID} from ${GRAFANA_URL}..."
curl -sf -u "${GRAFANA_USER}:${GRAFANA_PASS}" \
  "${GRAFANA_URL}/api/dashboards/uid/${DASHBOARD_UID}" \
  | python3 -c "
import sys, json
dash = json.load(sys.stdin)['dashboard']
for key in ['id', 'version']:
    dash.pop(key, None)
print(json.dumps(dash, indent=2))
" > "${JSON_FILE}"

panels=$(python3 -c "import json; print(len(json.load(open('${JSON_FILE}'))['panels']))")
echo "Exported ${panels} panels to ${JSON_FILE}"

echo "Generating ConfigMap..."
python3 -c "
import json

with open('${JSON_FILE}') as f:
    dashboard_json = f.read()

indented = '\n'.join('    ' + line for line in dashboard_json.splitlines())

cm_yaml = f'''apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-claude-code
  labels:
    grafana_dashboard: \"1\"
  annotations:
    grafana_folder: \"Claude Code\"
data:
  claude-code.json: |
{indented}
'''

with open('${CM_FILE}', 'w') as f:
    f.write(cm_yaml)
"

echo "ConfigMap written to ${CM_FILE}"
echo "Done. Commit and push to sync via ArgoCD."
