
PROJECT = ska-mid-cbf-fhs-system-tests

PYTHON_RUNNER = poetry run python -m
POETRY_PYTHON_RUNNER = poetry run python -m

# KUBE_NAMESPACE defines the Kubernetes Namespace that will be deployed to
# using Helm.  If this does not already exist it will be created
KUBE_NAMESPACE ?= ska-mid-cbf-fhs-system-tests

# UMBRELLA_CHART_PATH Path of the umbrella chart to work with
HELM_CHART ?= ska-mid-cbf-fhs-system-tests
UMBRELLA_CHART_PATH ?= charts/$(HELM_CHART)/

# RELEASE_NAME is the release that all Kubernetes resources will be labelled with
RELEASE_NAME = $(HELM_CHART)

KUBE_APP ?= ska-mid-cbf-fhs-system-tests

TARANTA ?= false
BOOGIE ?= false
MINIKUBE ?= false
K3D ?= false

# Expose All Tango Services to the external network (enable Loadbalancer service)
EXPOSE_All_DS ?= true

SKA_TANGO_OPERATOR ?= true

# Chart for testing
K8S_CHART ?= $(HELM_CHART)
K8S_CHARTS ?= $(K8S_CHART)
K8S_TIMEOUT ?= 600s

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

# include your own private variables for custom deployment configuration
-include PrivateRules.mak

# pipeline job id
CI_JOB_ID ?= local

# TANGO_HOST connection to the Tango DS
TANGO_HOST ?= databaseds-tango-base:10000

# Domain used for naming Tango Device Servers, Emulator APIs, rabbitmq host, etc.
CLUSTER_DOMAIN ?= cluster.local

# W503: "Line break before binary operator." Disabled to work around a bug in flake8 where currently both "before" and "after" are disallowed.
PYTHON_SWITCHES_FOR_FLAKE8 = --ignore=DAR201,W503,E731

# F0002, F0010: Astroid errors. Not our problem.
# E0401: Import errors. Ignore for now until we figure out our actual project structure.
# E0611: Name not found in module. This occurs in our pipeline because the image we pull down uses an older version of Python; we should remove this immediately once we have our image building to CAR.
PYTHON_SWITCHES_FOR_PYLINT = --disable=E0401,E0611,F0002,F0010,E0001,E1101,C0114,C0115,C0116
PYTHON_SWITCHES_FOR_PYLINT_LOCAL = --disable=E0401,F0002,F0010,E1101,C0114,C0115,C0116

PYTHON_LINT_TARGET = tests/

CHART_FILE=charts/ska-mid-cbf-fhs-system-tests/Chart.yaml
CAR_REGISTRY=artefact.skao.int
HELM_INTERNAL_REPO=https://${CAR_REGISTRY}/repository/helm-internal


# uncomment to force a specific hash & override the automatic hash lookup (e.g. for testing a commit to a non-main branch)
FHS_VCC_HASH_VERSION = "0.1.0-dev.cf2800d9b"
EMULATORS_HASH_VERSION = "0.6.0-dev.c9401e8a9"

# Use Gitlab API to extract latest tags and builds from the main branch for the various repositories, to extract the hash versions
FHS_VCC_HELM_REPO=https://gitlab.com/api/v4/projects/58443798/packages/helm/dev
FHS_VCC_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/58443798/repository/tags | jq -r '.[0] | .name')
FHS_VCC_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/58443798/repository/branches/main | jq -r .commit.short_id)
FHS_VCC_HASH_VERSION?=$(FHS_VCC_LATEST_TAG)-dev.c$(FHS_VCC_LATEST_COMMIT)

EMULATORS_HELM_REPO=https://gitlab.com/api/v4/projects/55081836/packages/helm/dev
EMULATORS_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/55081836/repository/tags | jq -r '.[0] | .name')
EMULATORS_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/55081836/repository/branches/main | jq -r .commit.short_id)
EMULATORS_HASH_VERSION?=$(EMULATORS_LATEST_TAG)-dev.c$(EMULATORS_LATEST_COMMIT)

# TODO determine if we will use internal schemas at all
INTERNAL_SCHEMA_LATEST_TAG:=$(shell curl -s https://gitlab.com/api/v4/projects/47018613/repository/tags | jq -r '.[0] | .name')
INTERNAL_SCHEMA_LATEST_COMMIT:=$(shell curl -s https://gitlab.com/api/v4/projects/47018613/repository/branches/main | jq -r .commit.short_id)
INTERNAL_SCHEMA_HASH_VERSION?=$(INTERNAL_SCHEMA_LATEST_TAG)+dev.c$(INTERNAL_SCHEMA_LATEST_COMMIT)
CURR_INTERNAL_SCHEMA_VERSION:=$(shell grep ska-mid-cbf-internal-schemas pyproject.toml | awk -F '"' '{print $$2}')


K8S_CHART_PARAMS = --set global.minikube=$(MINIKUBE) \
	--set global.k3d=$(K3D) \
	--set global.exposeAllDS=$(EXPOSE_All_DS) \
	--set global.tango_host=$(TANGO_HOST) \
	--set global.cluster_domain=$(CLUSTER_DOMAIN) \
	--set global.operator=$(SKA_TANGO_OPERATOR) \
	--set ska-mid-cbf-fhs-vcc.hostInfo.clusterDomain=$(CLUSTER_DOMAIN) \
	--set ska-mid-cbf-fhs-vcc.properties.emulatorBaseUrl="$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN):5001" \
	--set ska-mid-cbf-fhs-vcc-boogie.enabled=$(BOOGIE) \
	--set global.labels.app=$(KUBE_APP) \
	--set ska-mid-cbf-emulators.emulator.labels.app=$(KUBE_APP) \
	--set ska-mid-cbf-emulators.injector.labels.app=$(KUBE_APP) \
	--set ska-mid-cbf-emulators.rabbitmq.host="rabbitmq-service.$(KUBE_NAMESPACE).svc.$(CLUSTER_DOMAIN)"

# Update the Chart.yaml and values.yaml for the repositories. If set to true, to use the latest tag versions from main branch on Gitlab
USE_DEV_BUILD ?= true

DEV_BUILD_PARAMS =  --set ska-mid-cbf-fhs-vcc.midcbf.image.tag=$(FHS_VCC_HASH_VERSION) \
					--set ska-mid-cbf-emulators.emulator.image.tag=$(EMULATORS_HASH_VERSION) \
					--set ska-mid-cbf-emulators.injector.image.tag=$(EMULATORS_HASH_VERSION) \
					
TAG_BUILD_PARAMS =  --set ska-mid-cbf-fhs-vcc.midcbf.image.tag=$(FHS_VCC_LATEST_TAG) \
					--set ska-mid-cbf-fhs-vcc.midcbf.image.registry=$(CAR_REGISTRY) \
					--set ska-mid-cbf-fhs-vcc-boogie.image.tag=$(FHS_VCC_LATEST_TAG) \
					--set ska-mid-cbf-fhs-vcc-boogie.image.registry=$(CAR_REGISTRY) \
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

PYTEST_MARKER = nightly

PYTEST_LOG_LEVEL = INFO
PYTHON_VARS_AFTER_PYTEST = -m "$(PYTEST_MARKER)" -s --namespace $(KUBE_NAMESPACE) --cluster_domain $(CLUSTER_DOMAIN) --tango_host $(TANGO_HOST) -v -rA --no-cov --log-cli-level=$(PYTEST_LOG_LEVEL)
PYTHON_LINE_LENGTH = 180

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
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc-boogie").version) = "$(FHS_VCC_LATEST_TAG)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc-boogie").repository) = "$(HELM_INTERNAL_REPO)"' $(CHART_FILE); \
		echo "Updating Chart.yaml to change ska-mid-cbf-emulators version to $(EMULATORS_LATEST_TAG) and repository to $(HELM_INTERNAL_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").version) = "$(EMULATORS_LATEST_TAG)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").repository) = "$(HELM_INTERNAL_REPO)"' $(CHART_FILE); \
	else \
		echo "Updating Chart.yaml to change ska-mid-cbf-fhs-vcc version to $(FHS_VCC_HASH_VERSION) and repository to $(FHS_VCC_HELM_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").version) = "$(FHS_VCC_HASH_VERSION)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc").repository) = "$(FHS_VCC_HELM_REPO)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc-boogie").version) = "$(FHS_VCC_HASH_VERSION)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-fhs-vcc-boogie").repository) = "$(FHS_VCC_HELM_REPO)"' $(CHART_FILE); \
		echo "Updating Chart.yaml to change ska-mid-cbf-emulators version to $(EMULATORS_HASH_VERSION) and repository to $(EMULATORS_HELM_REPO)"; \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").version) = "$(EMULATORS_HASH_VERSION)"' $(CHART_FILE); \
		yq eval -i '(.dependencies[] | select(.name == "ska-mid-cbf-emulators").repository) = "$(EMULATORS_HELM_REPO)"' $(CHART_FILE); \
	fi
	cat $(CHART_FILE)

check-minikube-eval:
	@minikube status | grep -iE '^.*(docker-env: in-use).*$$'; \
	if [ $$? -ne 0 ]; then \
		echo "Minikube docker-env not active. Please run: 'eval \$$(minikube docker-env)'."; \
		exit 1; \
	else echo "Minikube docker-env is active."; \
	fi

k8s-pre-install-chart:
	@if [ "$(MINIKUBE)" = "true" ]; then make check-minikube-eval; fi;
	rm -f charts/ska-mid-cbf-fhs-system-tests/Chart.lock
	make update-chart FHS_VCC_HASH_VERSION=$(FHS_VCC_HASH_VERSION) EMULATORS_HASH_VERSION=$(EMULATORS_HASH_VERSION)

k8s-deploy:
	make k8s-install-chart MINIKUBE=$(MINIKUBE) K3D=$(K3D) USE_DEV_BUILD=$(USE_DEV_BUILD) BOOGIE=$(BOOGIE)
	@echo "Waiting for all pods in namespace $(KUBE_NAMESPACE) to be ready..."
	@time kubectl wait pod --all --for=condition=Ready --timeout=15m0s --namespace $(KUBE_NAMESPACE)


k8s-deploy-dev: MINIKUBE=true
K8s-deploy-dev: K3D=false
k8s-deploy-dev:
	make k8s-deploy MINIKUBE=$(MINIKUBE) K3D=$(K3D) USE_DEV_BUILD=true BOOGIE=true

k8s-destroy:
	make k8s-uninstall-chart
	@echo "Waiting for all pods in namespace $(KUBE_NAMESPACE) to terminate..."
	@time kubectl wait pod --all --for=delete --timeout=5m0s --namespace $(KUBE_NAMESPACE)

python-pre-test:
	mkdir -p build/reports
	make update-internal-schema
	poetry show ska-mid-cbf-internal-schemas > build/reports/internal_schemas_version.txt
	cat build/reports/internal_schemas_version.txt | grep version

python-do-test:
	@$(PYTHON_RUNNER) pytest --version -c /dev/null
	$(PYTHON_VARS_BEFORE_PYTEST) $(PYTHON_RUNNER) pytest $(PYTHON_VARS_AFTER_PYTEST) $(PYTHON_TEST_FILE)

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

format-and-lint:
	make format-python
	make lint-python-local
