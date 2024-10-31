from logging import Logger

import pytest
from connection_utils import DeviceKey, create_proxy, get_emulator_url, get_fqdn
from ska_tango_testing.integration import TangoEventTracer


class BaseTangoTestClass:

    @pytest.fixture()
    def initialize_with_indices(self, request, logger: Logger, emulator_base_url: str) -> None:
        idxs = request.param
        self.idxs = idxs if isinstance(idxs, list) else [idxs]

        self.logger = logger
        self.fqdns = {k: {i: get_fqdn(i, k) for i in self.idxs} for k in DeviceKey}
        self.proxies = {k: {i: create_proxy(i, k) for i in self.idxs} for k in DeviceKey}
        self.emulator_urls = {i: get_emulator_url(i, emulator_base_url) for i in self.idxs}

        self.pre_initialize()

        self.event_tracer = TangoEventTracer()

        for i in self.idxs:
            all_bands_fqdn = self.fqdns[DeviceKey.ALL_BANDS][i]
            self.event_tracer.subscribe_event(all_bands_fqdn, "longRunningCommandResult")
            self.event_tracer.subscribe_event(all_bands_fqdn, "adminMode")
            self.event_tracer.subscribe_event(all_bands_fqdn, "state")
            self.event_tracer.subscribe_event(all_bands_fqdn, "obsState")
            self.event_tracer.subscribe_event(all_bands_fqdn, "communicationState")

        self.post_initialize()

    def pre_initialize(self):
        """Testclass-specific pre-initialization. Runs after proxies and FQDNs are setup but before any other actions."""

    def post_initialize(self):
        """Testclass-specific post-initialization. Runs immediately following all other initialization."""
