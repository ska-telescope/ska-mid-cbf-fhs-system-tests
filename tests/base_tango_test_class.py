from logging import Logger

import pytest
from connection_utils import DeviceKey, create_proxy, get_emulator_url, get_fqdn
from ska_tango_testing.integration import TangoEventTracer


class BaseTangoTestClass:

    @pytest.fixture(scope="session")
    def all_proxies(self, logger: Logger):
        # Pre-load all combinations for indices 1-6
        logger.info("Creating proxies for all devices...")
        proxies_cache = {(i,): {k: {i: create_proxy(i, k)} for k in DeviceKey} for i in range(1, 13)}
        logger.info("Proxies created.")
        return proxies_cache

    @pytest.fixture()
    def initialize_with_indices(self, request, logger: Logger, emulator_base_url: str, all_proxies) -> None:
        idxs = request.param
        self.loaded_idxs = idxs if isinstance(idxs, list) else [idxs]
        self.logger = logger

        self.fqdns = {k: {i: get_fqdn(i, k) for i in self.loaded_idxs} for k in DeviceKey}

        self.proxies = {k: {i: all_proxies[(i,)][k][i] for i in self.loaded_idxs} for k in DeviceKey}

        self.emulator_urls = {i: get_emulator_url(i, emulator_base_url) for i in self.loaded_idxs}

        self.pre_initialize()

        self.event_tracer = TangoEventTracer()

        for i in self.loaded_idxs:
            all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][i]
            self.event_tracer.subscribe_event(all_bands_fqdn, "longRunningCommandResult")
            self.event_tracer.subscribe_event(all_bands_fqdn, "adminMode")
            self.event_tracer.subscribe_event(all_bands_fqdn, "state")
            self.event_tracer.subscribe_event(all_bands_fqdn, "obsState")
            self.event_tracer.subscribe_event(all_bands_fqdn, "communicationState")
            self.event_tracer.subscribe_event(all_bands_fqdn, "healthState")

        self.post_initialize()

    def pre_initialize(self):
        """Testclass-specific pre-initialization. Runs after proxies and FQDNs are setup but before any other actions."""

    def post_initialize(self):
        """Testclass-specific post-initialization. Runs immediately following all other initialization."""
