#!/bin/bash
set -Eeo pipefail
trap cleanup ERR EXIT
##
# This script creates a kubeconfig file associated with a service account within passed namespaces
# The kubeconfig file is uploaded to the Nexus repository and the url of the file is printed out
# It will expect the namespace to be in the following format:
#   ci-<project_name>-<branch_name>
#
# Usage:
# namespace_auth.sh <service_account_name> <Namespace-1> <Namespace-2> .. <Namespace-n>
#
# Note: The first namespace should have been created previously and all role/rolebinding/secret/serviceaccount
# resources with the ${SERVICE_ACCOUNT_NAME}-* is deleted
#
# Additional documentation on the steps below:
# - https://kubernetes.io/docs/reference/access-authn-authz/authentication/
# - https://kubernetes.io/docs/reference/access-authn-authz/certificate-signing-requests/
# - https://kubernetes.io/docs/reference/access-authn-authz/rbac/
# - https://kubernetes.io/docs/reference/access-authn-authz/service-accounts-admin/
##

# Check if the necessary arguments, service account name and namespace is passed
check_arguments() {
  if [[ -z "$SERVICE_ACCOUNT_NAME" ]]; then
    ERR_MESSAGE="Missing arguments: service_account_name
    usage: $0 <service_account_name> <Namespace>"
    exit 1
  fi
  if [[ -z "$NAMESPACE" ]]; then
    ERR_MESSAGE="Missing arguments: Namespace
    usage: $0 <service_account_name> <Namespace>"
    exit 1
  fi
}

# Check if namespace is correct
check_namespaces() {
  for NS in "${NAMESPACES[@]}"; do
    if [[ ${NS} != dev-shared-* ]] && \
       [[ ${NS} != ci-${CI_PROJECT_NAME}-${CI_COMMIT_REF_SLUG}* ]] && \
       [[ ${NS} != ci-${CI_PROJECT_NAME}-${CI_JOB_ID}* ]] && \
       [[ ${NS} != ci-${CI_PROJECT_NAME}-${CI_PIPELINE_ID}* ]] && \
       [[ ${NS} != ci-${CI_PROJECT_NAME}-${CI_COMMIT_SHORT_SHA}* ]]; then
      ERR_MESSAGE="Namespace is not following an expected format: dev-shared-*, ci-<project_name>-<branch name>*, ci-<project_name>-<gitlab job id>*, ci-<project_name>-<gitlab pipeline id>*, ci-<project_name>-<commit short SHA>* actual: $NS, expected: one of [ci-${CI_PROJECT_NAME}-${CI_COMMIT_REF_SLUG}*, ci-${CI_PROJECT_NAME}-${CI_JOB_ID}*, ci-${CI_PROJECT_NAME}-${CI_PIPELINE_ID}*, ci-${CI_PROJECT_NAME}-${CI_COMMIT_SHORT_SHA}*] $"
      exit 1
    fi
    echo "Checking if the namespace: ${NS} exists..."
    kubectl describe namespace ${NS}
    echo "...done"
  done
}

# Delete existing resources in a fail-safe manner
delete_existing_resources() {
    for ns in "${NAMESPACES[@]}"; do
        kubectl -n ${ns} delete --ignore-not-found rolebinding/${SERVICE_ACCOUNT_NAME}-ns-admin
        kubectl -n ${ns} delete --ignore-not-found role/${SERVICE_ACCOUNT_NAME}-ns-admin
        kubectl -n ${ns} delete --ignore-not-found secret/${SERVICE_ACCOUNT_NAME}-secret
        kubectl -n ${ns} delete --ignore-not-found serviceaccount/${SERVICE_ACCOUNT_NAME}
    done
}

# Utility function to delete namespaces starting with the passed argument
delete_namespaces() {
    if [[ -z "$1" ]]; then
    ERR_MESSAGE="Missing namespace parameter!
    usage: $0 <namespace_template>"
      exit 1
    fi
    echo "Deleting the previous namespaces with the names in $1 format (Ignore any errors here!)..."
    kubectl get namespace -o name | \
    grep $1 | grep -v ${NAMESPACE} | \
    xargs kubectl delete || true
    echo "...done"
}

# Create temporary target directory to hold files (kubeconfig, tokens etc,)
create_target_folder() {
    echo -n "Creating target directory to hold files in ${TARGET_FOLDER}..."
    mkdir -p "${TARGET_FOLDER}"
    printf "done"
}

# Create the service account with name from variable ${SERVICE_ACCOUNT_NAME} and
# necessary Role resources
create_service_account() {
    echo -e "\\nCreating a service account in ${NAMESPACE} namespace: ${SERVICE_ACCOUNT_NAME}"
    kubectl --namespace "${NAMESPACE}" create sa "${SERVICE_ACCOUNT_NAME}"
    kubectl --namespace "${NAMESPACE}" apply -f - <<EOF
---
apiVersion: v1
kind: Secret
metadata:
  name: ${SERVICE_ACCOUNT_NAME}-token
  annotations:
    kubernetes.io/service-account.name: ${SERVICE_ACCOUNT_NAME}
type: kubernetes.io/service-account-token
EOF

    for ns in "${NAMESPACES[@]}"; do
        echo -e "\\nCreating rolebinding for ${ns} namespace: ${SERVICE_ACCOUNT_NAME}"
        kubectl --namespace "${ns}" apply -f - <<EOF

---

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  namespace: ${ns}
rules:
- apiGroups: [""]
  resources: ["namespaces", "storageclasses", "serviceaccounts",
              "resourcequotas", "persistentvolumes", "limitranges",
              "nodes", "componentstatuses"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["autoscaling"]
  resources: ["horizontalpodautoscalers"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["discovery.k8s.io"]
  resources: ["endpointslices"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["admissionregistration.k8s.io"]
  resources: ["mutatingwebhookconfigurations", "validatingwebhookconfigurations"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apiextensions.k8s.io"]
  resources: ["customresourcedefinitions"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apiregistration.k8s.io"]
  resources: ["apiservices"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apps"]
  resources: ["controllerrevisions"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["node.k8s.io"]
  resources: ["runtimeclasses"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["policy"]
  resources: ["poddisruptionbudgets", "podsecuritypolicies"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["rolebindings", "roles"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["storage.k8s.io"]
  resources: ["storageclasses", "volumeattachments"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["", "batch", "apps"]
  resources: ["deployments", "jobs", "pods", "pods/log", "pods/exec", "configmaps",
              "pods/portforward", "pods/attach", "persistentvolumeclaims", "services", "secrets",
              "endpoints", "events", "podtemplates", "replicationcontrollers",
              "daemonsets", "replicasets", "statefulsets", "cronjobs"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["events.k8s.io"]
  resources: ["events"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["extensions"]
  resources: ["ingresses"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingressclasses", "networkpolicies"]
  verbs: ["list", "get", "watch"]

---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  namespace: ${ns}
subjects:
- kind: ServiceAccount
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
roleRef:
  kind: Role
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  apiGroup: rbac.authorization.k8s.io

EOF
    done
  echo <<EOF
---
kind: RoleBinding
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  namespace: ${ns}
subjects:
- kind: ServiceAccount
  name: ${SERVICE_ACCOUNT_NAME}
  namespace: ${NAMESPACE}
roleRef:
  kind: Role
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  apiGroup: rbac.authorization.k8s.io
---

kind: Role
apiVersion: rbac.authorization.k8s.io/v1
metadata:
  name: ${SERVICE_ACCOUNT_NAME}-ns-admin
  namespace: ${ns}
rules:
- apiGroups: [""]
  resources: ["namespaces", "storageclasses", "serviceaccounts",
              "resourcequotas", "persistentvolumes", "limitranges",
              "nodes", "componentstatuses"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["autoscaling"]
  resources: ["horizontalpodautoscalers"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["discovery.k8s.io"]
  resources: ["endpointslices"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["admissionregistration.k8s.io"]
  resources: ["mutatingwebhookconfigurations", "validatingwebhookconfigurations"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apiextensions.k8s.io"]
  resources: ["customresourcedefinitions"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apiregistration.k8s.io"]
  resources: ["apiservices"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["apps"]
  resources: ["controllerrevisions"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["node.k8s.io"]
  resources: ["runtimeclasses"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["policy"]
  resources: ["poddisruptionbudgets", "podsecuritypolicies"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["rbac.authorization.k8s.io"]
  resources: ["rolebindings", "roles"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["storage.k8s.io"]
  resources: ["storageclasses", "volumeattachments"]
  verbs: ["list", "get", "watch"]
- apiGroups: ["", "batch", "apps"]
  resources: ["deployments", "jobs", "pods", "pods/log", "pods/exec", "configmaps",
              "pods/portforward", "pods/attach", "persistentvolumeclaims", "services", "secrets",
              "endpoints", "events", "podtemplates", "replicationcontrollers",
              "daemonsets", "replicasets", "statefulsets", "cronjobs"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["events.k8s.io"]
  resources: ["events"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["extensions"]
  resources: ["ingresses"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingresses"]
  verbs: ["list", "get", "watch", "create", "update", "patch", "delete"]
- apiGroups: ["networking.k8s.io"]
  resources: ["ingressclasses", "networkpolicies"]
  verbs: ["list", "get", "watch"]

EOF
}

# Extract secretname from the service account to get certificate
get_secret_name_from_service_account() {
    SECRET_NAME="${SERVICE_ACCOUNT_NAME}-token"
    echo "Secret name: ${SECRET_NAME}"
}

# Extract the certificate from secret to get user token
extract_ca_crt_from_secret() {
    echo -e -n "\\nExtracting ca.crt from secret..."
    kubectl --namespace "${NAMESPACE}" get secret "${SECRET_NAME}" -o json | jq \
    -r '.data["ca.crt"]' | base64 -d > "${TARGET_FOLDER}/ca.crt"
    printf "done"
}

# Extract user token from the secret to set kubeconfig values for outside access
get_user_token_from_secret() {
    echo -e -n "\\nGetting user token from secret..."
    USER_TOKEN=$(kubectl --namespace "${NAMESPACE}" get secret "${SECRET_NAME}" -o json | jq -r '.data["token"]' | base64 -d)
    printf "done"
}

# Create a kubeconfig file for the serviceaccount that can access the namespace, i.e. you don't need to specify --namespace using this token
set_kube_config_values() {
    context=$(kubectl config current-context)
    echo -e "\\nSetting current context to: $context"

    CLUSTER_NAME=$(kubectl config get-contexts "$context" | awk '{print $3}' | tail -n 1)
    echo "Cluster name: ${CLUSTER_NAME}"

    ENDPOINT=$(kubectl config view \
    -o jsonpath="{.clusters[?(@.name == \"${CLUSTER_NAME}\")].cluster.server}")
    echo "Endpoint: ${ENDPOINT}"

    # Set up the config
    echo -e "\\nPreparing k8s-${SERVICE_ACCOUNT_NAME}-${NAMESPACE}-conf kubeconfig file"
    echo -n "Setting a cluster entry in kubeconfig..."

    kubectl config set-cluster "${CLUSTER_NAME}" \
    --kubeconfig="${KUBECFG_FILE_PATH}" \
    --server="${ENDPOINT}" \
    --certificate-authority="${TARGET_FOLDER}/ca.crt" \
    --embed-certs=true

    echo -n "Setting token credentials entry in kubeconfig..."
    kubectl config set-credentials \
    "${SERVICE_ACCOUNT_NAME}-${NAMESPACE}-${CLUSTER_NAME}" \
    --kubeconfig="${KUBECFG_FILE_PATH}" \
    --token="${USER_TOKEN}"


    for ns in "${NAMESPACES[@]}"; do
        echo -n "Setting a context entry in kubeconfig in ${ns} namespace..."
        kubectl config set-context \
        "${SERVICE_ACCOUNT_NAME}-${ns}-${CLUSTER_NAME}" \
        --kubeconfig="${KUBECFG_FILE_PATH}" \
        --cluster="${CLUSTER_NAME}" \
        --user="${SERVICE_ACCOUNT_NAME}-${NAMESPACE}-${CLUSTER_NAME}" \
        --namespace="${ns}"
    done

    echo -n "Setting the current-context in the kubeconfig file..."
    kubectl config use-context --kubeconfig="${KUBECFG_FILE_PATH}" "${SERVICE_ACCOUNT_NAME}-${NAMESPACE}-${CLUSTER_NAME}"
}

# Push kubeconfig file to the Nexus Repo and get access url
push_kubeconfig_to_nexus() {
  if [[ -z "$LOCAL_NEXUS_CACHE" ]]; then
    # Define the cache if it's not defined previously, test cases can override this
    NEXUS_CACHE=http://192.168.99.204
  fi
  cd ${TARGET_FOLDER}
  echo -e "Uploading to Nexus Cache(${LOCAL_NEXUS_CACHE}) ${KUBECFG_FILE_NAME}...";
  curl -u $CAR_RAW_USERNAME:$CAR_RAW_PASSWORD --upload-file ${KUBECFG_FILE_NAME} ${LOCAL_NEXUS_CACHE}/repository/k8s-ci-creds-internal/${KUBECFG_FILE_NAME};
  echo "done"
  echo -e "${YELLOW}Note: The Nexus cache is only accessible for STFC Cluster at the moment.${NC}"
  echo -e "${YELLOW}Note: If you need additional clusters, please contact system team.${NC}"
  KUBECFG_URL="${LOCAL_NEXUS_CACHE}/repository/k8s-ci-creds-internal/${KUBECFG_FILE_NAME}"
}

# Delete temporary folder
delete_target_folder() {
  rm -rf ${TARGET_FOLDER}
}

# Things to do when an error occurs: Delete existing resources and temporary folder
cleanup() {
    exitcode=$?
    if [[ $exitcode != 0 ]]; then
      printf ${RED}${BAR}'!!  ERROR  !!'${BAR}
      printf ${YELLOW}"\n${ERR_MESSAGE}\nPlease also check a few lines above this ERROR"${NC}
      printf ${RED}'\nerror condition hit\n' 1>&2
      printf 'exit code returned: %s\n' "$exitcode"
      printf 'the command executing at the time of the error was: %s\n' "$BASH_COMMAND"
      printf 'command present on line: %d' "${BASH_LINENO[0]}"
      printf '\nYou can contact the SYSTEM team on Slack in #team-system-support about this error with this error log!\n'
      # Some more clean up code can be added here before exiting
      delete_existing_resources
      delete_target_folder
    fi
    exit $exitcode
}

main() {

  # Define variables
  SERVICE_ACCOUNT_NAME=$1
  shift
  NAMESPACES=("$@") # Save namespaces as array
  NAMESPACE="$1"

  TARGET_FOLDER="/tmp/kube"
  KUBECFG_FILE_NAME="k8s-${SERVICE_ACCOUNT_NAME}-${NAMESPACE}-conf"
  KUBECFG_FILE_PATH="${TARGET_FOLDER}/${KUBECFG_FILE_NAME}"
  KUBECFG_URL=""

  # Output formatting
  BAR="########################" # 24 characters
  RED='\033[0;31m'
  GREEN='\033[0;32m'
  CYAN='\033[0;36m'
  YELLOW='\033[0;033m'
  NC='\033[0m' # No Color

  echo -e "\\n${BAR}  Credential Generation  ${BAR}"
  echo "This script will generate credentials for the pipeline namespace."

  check_arguments
  check_namespaces
  delete_existing_resources
  create_target_folder
  create_service_account
  get_secret_name_from_service_account
  extract_ca_crt_from_secret
  get_user_token_from_secret
  set_kube_config_values
  push_kubeconfig_to_nexus

  echo -e "\\n\n${GREEN}${BAR}All done!${BAR}${NC}"
  echo -e "section_start:`date +%s`:permissions_section[collapsed=true]\r\e[0KYou have the following permissions(Expand this section):"
  kubectl --kubeconfig=${KUBECFG_FILE_PATH} auth can-i --list
  echo -e "section_end:`date +%s`:permissions_section\r\e[0K"
  echo "You can get the kubeconfig file from the url: \"${KUBECFG_URL}\" with the following command into your current directory in a file called KUBECONFIG:"
  echo -e "${CYAN}\tcurl ${KUBECFG_URL} --output KUBECONFIG"
  echo -e "${NC}Example usage:"
  echo -e "${CYAN}\tkubectl --kubeconfig=KUBECONFIG get pods${NC}"
  echo -e "${CYAN}Note: The current context is set to first namespace passed, you need to provide other namespaces explicitly (with \"-n namespace\" option)${NC}"

  delete_target_folder
}

main $@