# SKA MID CBF FHS System Tests

This repository is used for testing of the MID CBF FHS including emulators.

Code repository: [ska-mid-cbf-fhs-system-tests](https://gitlab.com/ska-telescope/ska-mid-cbf-fhs-system-tests)

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