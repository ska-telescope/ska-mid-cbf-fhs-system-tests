# SKA MID CBF FHS System Tests

This repository is used for testing of the MID CBF FHS including emulators.

Code repository: [ska-mid-cbf-fhs-system-tests](https://gitlab.com/ska-telescope/ska-mid-cbf-fhs-system-tests)

---

To run tests locally via minikube, run:
```bash
make k8s-install-chart MINIKUBE=true BOOGIE=true USE_DEV_BUILD=true
```
to deploy the charts (Tango, device servers, emulators), and then run
```bash
make python-test
```
to run the tests.

To tear down, run:
```bash
make k8s-destroy
```

---

To run manual tests in the pipeline, allow the build and lint stages to complete, then start the manual `k8s-on-demand-deploy` job to deploy the namespace to the SKA K8s cluster (viewable via Headlamp, check the job logs). Once this completes, you can run the `python-test` job and it will run the tests against that deployment on the cluster. Once the test job completes, the namespace will be scheduled for deletion in 10 minutes, but you can run that job manually as well to delete it sooner.

You can also use the `k8s-on-demand-destroy` manual job at any time to tear down the namespace (e.g. if a problem occurs during the deployment and causes the pipeline and namespace to get stuck), and the `k8s-on-demand-info` manual job to print details about the deployment.

---

To view debug logs when testing locally, add `PYTEST_LOG_LEVEL=DEBUG` when running the test command:
```bash
make python-test PYTEST_LOG_LEVEL=DEBUG
```
Other supported levels are `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG`.

---

To test locally with a custom bitstream (i.e. a branch in ska-mid-cbf-bitstreams), add e.g. the following under `ska-mid-cbf-fhs-vcc.lowLevel` in values.yaml:
```yaml
gitlab_bitstream_url_override: "https://gitlab.com/ska-telescope/ska-mid-cbf-bitstreams/-/archive/cip-2957/ska-mid-cbf-bitstreams-cip-2957.tar.gz?path=raw/ska-mid-cbf-agilex-vcc"
```

You can find this URL by navigating to the bitstream repo on GitLab (https://gitlab.com/ska-telescope/ska-mid-cbf-bitstreams), navigating into your branch, and then navigating into the raw/ska-mid-cbf-<bitstream_id> folder. Then click the "Code" dropdown, and copy the "tar.gz" link under "Download this directory". Alternatively, you can just copy the above and substitute in your branch name and bitstream ID.
