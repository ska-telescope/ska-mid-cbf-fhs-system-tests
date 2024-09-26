
PROJECT = ska-mid-cbf-fhs-system-tests

POETRY_PYTHON_RUNNER = poetry run python -m

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-cbf-fhs-system-tests
#KUBE_NAMESPACE_SDP ?= $(KUBE_NAMESPACE)-sdp

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
HELM_CHART ?= ska-mid-cbf-fhs-system-tests
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/

# RELEASE_NAME is the release that all Kubernetes resources will be labelled with
RELEASE_NAME = $(HELM_CHART)

KUBE_APP ?= ska-mid-cbf-fhs-system-tests

TARANTA ?= true # Enable Taranta
TARANTA_AUTH ?= false # Enable Taranta
MINIKUBE ?= false ## Minikube or not

LOADBALANCER_IP ?= 192.168.99.16
INGRESS_PROTOCOL ?= https
ifeq ($(strip $(MINIKUBE)),true)
LOADBALANCER_IP ?= $(shell minikube ip)
INGRESS_HOST ?= $(LOADBALANCER_IP)
INGRESS_PROTOCOL ?= http
endif

EXPOSE_All_DS ?= true ## Expose All Tango Services to the external network (enable Loadbalancer service)
SKA_TANGO_OPERATOR ?= true
SKA_TANGO_ARCHIVER ?= false ## Set to true to deploy EDA

# Chart for testing
K8S_CHART ?= $(HELM_CHART)
K8S_CHARTS ?= $(K8S_CHART)

TARGET_SITE ?= k8s

# include OCI Images support
include .make/oci.mk

# include k8s support
include .make/k8s.mk

# include Helm Chart support
include .make/helm.mk

# Include Python support
include .make/python.mk

# include raw support
include .make/raw.mk

# include core make support
include .make/base.mk

# include xray support
# include .make/xray.mk

# include your own private variables for custom deployment configuration
-include PrivateRules.mak

# ska-tango-archiver params for EDA deployment
# include archiver/archiver.mk 

TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set global.taranta_auth_enabled=$(TARANTA_AUTH) \
				 --set global.taranta_dashboard_enabled=$(TARANTA)

ifneq ($(MINIKUBE),)
ifneq ($(MINIKUBE),true)
TARANTA_PARAMS = --set ska-taranta.enabled=$(TARANTA) \
				 --set global.taranta_auth_enabled=$(TARANTA_AUTH) \
				 --set global.taranta_dashboard_enabled=$(TARANTA)
endif
endif

CI_JOB_ID ?= local##pipeline job id
TANGO_HOST ?= databaseds-tango-base:10000## TANGO_HOST connection to the Tango DS
CLUSTER_DOMAIN ?= cluster.local## Domain used for naming Tango Device Servers

#E203 is added for a whitespace error in tests/lib/utils/device_server_ping_test()
PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=E501,F407,W503,D100,D103,D400,DAR101,D104,D101,D107,D401,FS002,D200,DAR201,D202,D403,N802,DAR401,E203
PYTHON_SWITCHES_FOR_PYLINT = --disable=W0613,C0116,C0114,R0801,W0621,W1203,C0301,F0010,R1721,R1732
PYTHON_LINT_TARGET = tests/ test_parameters/

# ENGINEERING_CONSOLE_IMAGE_VER=$(shell kubectl describe pod/ds-deployer-deployer-0 -n $(KUBE_NAMESPACE) | grep 'Image:' | sed 's/.*\://')
# SIGNAL_VERIFICATION_IMAGE_VER=$(shell kubectl describe pod/sv -n $(KUBE_NAMESPACE) | grep ska-mid-cbf-signal-verification | grep 'Image:' | sed 's/.*\://')

CHART_FILE=charts/ska-mid-cbf-fhs-system-tests/Chart.yaml
CAR_REGISTRY=artefact.skao.int
HELM_INTERNAL_REPO=https://${CAR_REGISTRY}/repository/helm-internal

# Use Gitlab API to extract latest tags and builds from the main branch for the various repositories, to extract the hash versions
FHS_VCC_HELM_REPO=https://gitlab.com/api/v4/projects/58443798/packages/helm/dev
FHS_VCC_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/58443798/repository/tags | jq -r '.[0] | .name')
FHS_VCC_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/58443798/repository/branches/main | jq -r .commit.short_id)
FHS_VCC_HASH_VERSION?=$(FHS_VCC_LATEST_TAG)-dev.c$(FHS_VCC_LATEST_COMMIT)

EMULATORS_HELM_REPO=https://gitlab.com/api/v4/projects/55081836/packages/helm/dev
EMULATORS_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/55081836/repository/tags | jq -r '.[0] | .name')
EMULATORS_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/55081836/repository/branches/main | jq -r .commit.short_id)
EMULATORS_HASH_VERSION?=$(EMULATORS_LATEST_TAG)-dev.c$(EMULATORS_LATEST_COMMIT)

INTERNAL_SCHEMA_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/47018613/repository/tags | jq -r '.[0] | .name')
INTERNAL_SCHEMA_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/47018613/repository/branches/main | jq -r .commit.short_id)
INTERNAL_SCHEMA_HASH_VERSION?=$(INTERNAL_SCHEMA_LATEST_TAG)+dev.c$(INTERNAL_SCHEMA_LATEST_COMMIT)
CURR_INTERNAL_SCHEMA_VERSION:=$(shell grep ska-mid-cbf-internal-schemas pyproject.toml | awk -F '"' '{print $$2}')


K8S_EXTRA_PARAMS ?=
# K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
# 	--set global.exposeAllDS=$(EXPOSE_All_DS) \
# 	--set global.tango_host=$(TANGO_HOST) \
# 	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
# 	--set global.operator=$(SKA_TANGO_OPERATOR) \
# 	--set ska-sdp.helmdeploy.namespace=$(KUBE_NAMESPACE_SDP) \
# 	--set ska-sdp.ska-sdp-qa.zookeeper.clusterDomain=$(CLUSTER_DOMAIN) \
# 	--set ska-sdp.ska-sdp-qa.kafka.clusterDomain=$(CLUSTER_DOMAIN) \
# 	--set ska-sdp.ska-sdp-qa.redis.clusterDomain=$(CLUSTER_DOMAIN) \
# 	--set ska-mid-cbf-mcs.hostInfo.clusterDomain=$(CLUSTER_DOMAIN) \
# 	--set global.labels.app=$(KUBE_APP) \
# 	$(TARANTA_PARAMS)
K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.exposeAllDS=$(EXPOSE_All_DS) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-mid-cbf-fhs-vcc.hostInfo.clusterDomain=$(CLUSTER_DOMAIN) \
	--set global.labels.app=$(KUBE_APP) \
	--set ska-mid-cbf-emulators.rabbitmq.host="rabbitmq-service.$(KUBE_NAMESPACE).svc.cluster.local" \
	$(TARANTA_PARAMS)

# ifeq ($(SKA_TANGO_ARCHIVER),true)
# 	K8S_CHART_PARAMS += $(SKA_TANGO_ARCHIVER_PARAMS)
# endif

USE_DEV_BUILD ?= true # Update the Chart.yaml and values.yaml for the repositories. If set to true, to use the latest tag versions from main branch on Gitlab

DEV_BUILD_PARAMS =  --set ska-mid-cbf-fhs-vcc.midcbf.image.tag=$(FHS_VCC_HASH_VERSION) \
					--set ska-mid-cbf-emulators.emulator.image.tag=$(EMULATORS_HASH_VERSION) \
					--set ska-mid-cbf-emulators.injector.image.tag=$(EMULATORS_HASH_VERSION) \
					
TAG_BUILD_PARAMS =  --set ska-mid-cbf-fhs-vcc.midcbf.image.tag=$(FHS_VCC_LATEST_TAG) \
					--set ska-mid-cbf-fhs-vcc.midcbf.image.registry=$(CAR_REGISTRY) \
					--set ska-mid-cbf-emulators.emulator.image.tag=$(EMULATORS_LATEST_TAG) \
					--set ska-mid-cbf-emulators.emulator.image.registry=$(CAR_REGISTRY) \
					--set ska-mid-cbf-emulators.injector.image.tag=$(EMULATORS_LATEST_TAG) \
					--set ska-mid-cbf-emulators.injector.image.registry=$(CAR_REGISTRY) \

ifeq ($(USE_DEV_BUILD),true)
	K8S_CHART_PARAMS += $(DEV_BUILD_PARAMS)
else ifeq ($(USE_DEV_BUILD),false)
	K8S_CHART_PARAMS += $(TAG_BUILD_PARAMS)
endif

ifneq (,$(wildcard $(VALUES)))
	K8S_CHART_PARAMS += $(foreach f,$(wildcard $(VALUES)),--values $(f))
endif

TEST_ID = Test_1

PYTEST_MARKER = nightly

PYTHON_VARS_AFTER_PYTEST = -m $(PYTEST_MARKER) -s --cucumberjson=build/reports/cucumber.json --json-report --json-report-file=build/reports/report.json --namespace $(KUBE_NAMESPACE) --cluster_domain $(CLUSTER_DOMAIN) --tango_host $(TANGO_HOST) --test_id $(TEST_ID) -v -rpfs 

XRAY_TEST_RESULT_FILE = build/reports/cucumber.json

echo-charts:
	@echo $(K8S_CHART_PARAMS)

echo-internal-schema:
	@echo "INTERNAL_SCHEMA_LATEST_TAG = $(INTERNAL_SCHEMA_LATEST_TAG)"
	@echo "INTERNAL_SCHEMA_LATEST_COMMIT = $(INTERNAL_SCHEMA_LATEST_COMMIT)"
	@echo "INTERNAL_SCHEMA_HASH_VERSION = $(INTERNAL_SCHEMA_HASH_VERSION)"
	@echo "CURR_INTERNAL_SCHEMA_VERSION = $(CURR_INTERNAL_SCHEMA_VERSION)"

update-internal-schema:
	@if [ "$(USE_DEV_BUILD)" == "false" ]; then \
		echo "$(CURR_INTERNAL_SCHEMA_VERSION)"; \
		echo "Update ska-mid-cbf-internal-schemas source in pyproject.toml to use nexus-internal"; \
		sed -i '/ska-mid-cbf-internal-schemas/ s/version = "$(CURR_INTERNAL_SCHEMA_VERSION)"/version = "$(INTERNAL_SCHEMA_LATEST_TAG)"/' pyproject.toml; \
		sed -i '/ska-mid-cbf-internal-schemas/ s/source = "gitlab-internal-schemas"/source = "nexus-internal"/' pyproject.toml; \
		cat pyproject.toml; \
		poetry update ska-mid-cbf-internal-schemas; \
	elif [ "$(USE_DEV_BUILD)"  == "true" ] && [ $(CURR_INTERNAL_SCHEMA_VERSION) != $(INTERNAL_SCHEMA_HASH_VERSION) ]; then \
		echo "Update ska-mid-cbf-internal-schemas version in pyproject.toml to use $(INTERNAL_SCHEMA_HASH_VERSION)"; \
		sed -i '/ska-mid-cbf-internal-schemas/ s/version = "$(CURR_INTERNAL_SCHEMA_VERSION)"/version = "$(INTERNAL_SCHEMA_HASH_VERSION)"/' pyproject.toml; \
		cat pyproject.toml; \
		poetry update ska-mid-cbf-internal-schemas; \
	else \
		echo "No changes needed to pyproject.toml for ska-mid-cbf-internal-schemas"; \
	fi

update-chart:
	@if [ "$(USE_DEV_BUILD)" == "false" ]; then \
		echo "Updating Chart.yaml to change ska-mid-cbf-fhs-vcc version to $(FHS_VCC_LATEST_TAG) and repository to $(HELM_INTERNAL_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").version) = "$(FHS_VCC_LATEST_TAG)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").repository) = "$(HELM_INTERNAL_REPO)"' $(CHART_FILE); \
		echo "Updating Chart.yaml to change ska-mid-cbf-emulators version to $(EMULATORS_LATEST_TAG) and repository to $(HELM_INTERNAL_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").version) = "$(EMULATORS_LATEST_TAG)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").repository) = "$(HELM_INTERNAL_REPO)"' $(CHART_FILE); \
	else \
		echo "Updating Chart.yaml to change ska-mid-cbf-fhs-vcc version to $(FHS_VCC_HASH_VERSION) and repository to $(FHS_VCC_HELM_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").version) = "$(FHS_VCC_HASH_VERSION)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").repository) = "$(FHS_VCC_HELM_REPO)"' $(CHART_FILE); \
		echo "Updating Chart.yaml to change ska-mid-cbf-emulators version to $(EMULATORS_HASH_VERSION) and repository to $(EMULATORS_HELM_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").version) = "$(EMULATORS_HASH_VERSION)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").repository) = "$(EMULATORS_HELM_REPO)"' $(CHART_FILE); \
	fi
	cat $(CHART_FILE)

k8s-pre-install-chart:
# @echo "k8s-pre-install-chart: creating the SDP namespace $(KUBE_NAMESPACE_SDP)"
# @make k8s-namespace KUBE_NAMESPACE=$(KUBE_NAMESPACE_SDP)
	make update-chart FHS_VCC_HASH_VERSION=$(FHS_VCC_HASH_VERSION) EMULATORS_HASH_VERSION=$(EMULATORS_HASH_VERSION)

#k8s-pre-install-chart-car:
# @echo "k8s-pre-install-chart-car: creating the SDP namespace $(KUBE_NAMESPACE_SDP)"
# @make k8s-namespace KUBE_NAMESPACE=$(KUBE_NAMESPACE_SDP)

# k8s-pre-uninstall-chart:
# 	@echo "k8s-post-uninstall-chart: deleting the SDP namespace $(KUBE_NAMESPACE_SDP)"
# 	@if [ "$(KEEP_NAMESPACE)" != "true" ]; then make k8s-delete-namespace KUBE_NAMESPACE=$(KUBE_NAMESPACE_SDP); fi

python-pre-test:
# @echo "Update dish_packet_capture_$(TARGET_SITE).yaml using ENGINEERING_CONSOLE_IMAGE_VER set to $(ENGINEERING_CONSOLE_IMAGE_VER)"
# @if [ "$(USE_DEV_BUILD)" == "false" ]; then \
# 	echo "and image set to $(EC_CAR_REGISTRY)"; \
# 	cat charts/ska-mid-cbf-fhs-system-tests/resources/dish_packet_capture_$(TARGET_SITE).yaml | sed -e "s|${EC_REGISTRY_REPO}/ska-mid-cbf-engineering-console|${EC_CAR_REGISTRY}|" -e "s|ENGINEERING_CONSOLE_IMAGE_VER|${ENGINEERING_CONSOLE_IMAGE_VER}|" > dish_packet_capture_temp.yaml; \
# else \
# 	cat charts/ska-mid-cbf-fhs-system-tests/resources/dish_packet_capture_$(TARGET_SITE).yaml | sed -e "s|ENGINEERING_CONSOLE_IMAGE_VER|${ENGINEERING_CONSOLE_IMAGE_VER}|" > dish_packet_capture_temp.yaml; \
# fi
# cat dish_packet_capture_temp.yaml
# @echo "Update visibilities_pod_$(TARGET_SITE).yaml using SIGNAL_VERIFICATION_IMAGE_VER set to $(SIGNAL_VERIFICATION_IMAGE_VER)"
# @if [ "$(USE_DEV_BUILD)" == "false" ]; then \
# 	echo "and image set to $(SV_CAR_REGISTRY)"; \
# 	cat charts/ska-mid-cbf-fhs-system-tests/resources/visibilities_pod_$(TARGET_SITE).yaml | sed -e "s|${SV_REGISTRY_REPO}/ska-mid-cbf-signal-verification-visibility-capture|${SV_CAR_REGISTRY}|" -e "s|SIGNAL_VERIFICATION_IMAGE_VER|${SIGNAL_VERIFICATION_IMAGE_VER}|" > visibilities_pod_temp.yaml; \
# else \
# 	cat charts/ska-mid-cbf-fhs-system-tests/resources/visibilities_pod_$(TARGET_SITE).yaml | sed -e "s|SIGNAL_VERIFICATION_IMAGE_VER|${SIGNAL_VERIFICATION_IMAGE_VER}|" > visibilities_pod_temp.yaml; \
# fi
# cat visibilities_pod_temp.yaml
	make update-internal-schema
	poetry show ska-mid-cbf-internal-schemas > build/reports/internal_schemas_version.txt
	cat build/reports/internal_schemas_version.txt | grep version

# python-post-test:
# 	rm dish_packet_capture_temp.yaml
# 	rm visibilities_pod_temp.yaml

run-pylint:
	pylint --output-format=parseable tests/ test_parameters/ | tee build/code_analysis.stdout

vars:
	$(info ##### Mid deploy vars)
	@echo "$(VARS)" | sed "s#VAR_#\n#g"

links:
	@echo ${CI_JOB_NAME}
	@echo "############################################################################"
	@echo "#            Access the Skampi landing page here:"
	@echo "#            $(INGRESS_PROTOCOL)://$(INGRESS_HOST)/$(KUBE_NAMESPACE)/start/"
	@echo "#     NOTE: Above link will only work if you can reach $(INGRESS_HOST)"
	@echo "############################################################################"
	@if [[ -z "${LOADBALANCER_IP}" ]]; then \
		exit 0; \
	elif [[ $(shell curl -I -s -o /dev/null -I -w \'%{http_code}\' http$(S)://$(LOADBALANCER_IP)/$(KUBE_NAMESPACE)/start/) != '200' ]]; then \
		echo "ERROR: http://$(LOADBALANCER_IP)/$(KUBE_NAMESPACE)/start/ unreachable"; \
		exit 10; \
	fi

format-python:
	$(POETRY_PYTHON_RUNNER) isort --profile black --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(PYTHON_LINT_TARGET)
	$(POETRY_PYTHON_RUNNER) black --exclude .+\.ipynb --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(PYTHON_LINT_TARGET)

lint-python-local:
	poetry install
	mkdir -p build/lint-output
	@echo "Linting..."
	-@ISORT_ERROR=0 BLACK_ERROR=0 FLAKE_ERROR=0 PYLINT_ERROR=0; \
	$(POETRY_PYTHON_RUNNER) isort --check-only --profile black --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_ISORT) $(PYTHON_LINT_TARGET) &> build/lint-output/1-isort-output.txt; \
	if [ $$? -ne 0 ]; then ISORT_ERROR=1; fi; \
	$(POETRY_PYTHON_RUNNER) black --exclude .+\.ipynb --check --line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_BLACK) $(PYTHON_LINT_TARGET) &> build/lint-output/2-black-output.txt; \
	if [ $$? -ne 0 ]; then BLACK_ERROR=1; fi; \
	$(POETRY_PYTHON_RUNNER) flake8 --show-source --statistics --max-line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_FLAKE8) $(PYTHON_LINT_TARGET) &> build/lint-output/3-flake8-output.txt; \
	if [ $$? -ne 0 ]; then FLAKE_ERROR=1; fi; \
	$(POETRY_PYTHON_RUNNER) pylint --output-format=parseable --max-line-length $(PYTHON_LINE_LENGTH) $(PYTHON_SWITCHES_FOR_PYLINT_LOCAL) $(PYTHON_LINT_TARGET) &> build/lint-output/4-pylint-output.txt; \
	if [ $$? -ne 0 ]; then PYLINT_ERROR=1; fi; \
	if [ $$ISORT_ERROR -ne 0 ]; then echo "Isort lint errors were found. Check build/lint-output/1-isort-output.txt for details."; fi; \
	if [ $$BLACK_ERROR -ne 0 ]; then echo "Black lint errors were found. Check build/lint-output/2-black-output.txt for details."; fi; \
	if [ $$FLAKE_ERROR -ne 0 ]; then echo "Flake8 lint errors were found. Check build/lint-output/3-flake8-output.txt for details."; fi; \
	if [ $$PYLINT_ERROR -ne 0 ]; then echo "Pylint lint errors were found. Check build/lint-output/4-pylint-output.txt for details."; fi; \
	if [ $$ISORT_ERROR -eq 0 ] && [ $$BLACK_ERROR -eq 0 ] && [ $$FLAKE_ERROR -eq 0 ] && [ $$PYLINT_ERROR -eq 0 ]; then echo "Lint was successful. Check build/lint-output for any additional details."; fi;


# k8s-namespace: ## create the kubernetes namespace
# 	@if [ "true" == "$(K8S_SKIP_NAMESPACE)" ]; then \
# 		echo "k8s-namespace: Namespace checks are skipped!"; \
# 	else \
# 		. $(K8S_SUPPORT); \
# 		KUBE_NAMESPACE=$(KUBE_NAMESPACE); \
# 		echo "KUBE_NAMESPACE: $$KUBE_NAMESPACE"; \
# 		if [ "$$CI" != "true" ]; then \
# 			echo "CI is true"; \
# 			kubectl get namespace $$KUBE_NAMESPACE > /dev/null 2>&1; \
# 			if [ $$? -eq 0 ]; then \
# 				echo "Kubectl get succeeded"; \
# 				kubectl describe namespace $$KUBE_NAMESPACE; \
# 				echo "Described"; \
# 				return; \
# 			fi; \
# 			kubectl create namespace $$KUBE_NAMESPACE; \
# 			echo "Created"; \
# 			return; \
# 		fi; \
# 		echo "createNamespace: Creating labeled namespace ..."; \
# 		export CICD_DOMAIN="cicd.skao.int"; \
# 		export MERGE_REQUEST_ASSIGNEES=""; \
# 		if [ ! -z "$(CI_MERGE_REQUEST_ID)" ]; then \
# 			export MERGE_REQUEST_ASSIGNEES="$(echo $$CI_MERGE_REQUEST_ASSIGNEES | sed -E 's/,? and /,/g; s/ //g')"; \
# 			echo "Merge request assignees: $$MERGE_REQUEST_ASSIGNEES"; \
# 		fi; \
# 		echo "PWD is: $$PWD"; \
# 		echo "$(cat ./resources/namespace.yml | envsubst)"; \
# 		export MY_VAR="$(echo "\${PWD}" | envsubst)"; \
# 		echo "My_VAR is: $$MY_VAR"; \
# 		echo "asdfghjkl"; \
# 		echo "${PWD}" | envsubst; \
# 		if [ $$? -eq 0 ]; then echo "envsubst successful"; else echo "envsubst failed"; fi; \
# 		echo "one"; \
# 		cat ./resources/namespace.yml; \
# 		echo "two"; \
# 		cat $$PWD/resources/namespace.yml; \
# 		echo "three"; \
# 		cat ./resources/namespace.yml | envsubst; \
# 		echo "four"; \
# 		cat $$PWD/resources/namespace.yml | envsubst; \
# 		echo "five"; \
# 		cat ./resources/namespace.yml | envsubst | kubectl apply -f -; \
# 		echo "Done!"; \
# 	fi;

# 	@cat ./resources/namespace.yml | envsubst
