"""
build_rtd_docs runs an RTD build for a specific project and ref. The goal
is to make sure that RTD can build the documentation, which ultimately is
what end-users see
"""

import logging
import os
import sys
import time
from typing import Tuple

import requests

LOGGING_FORMAT = "%(asctime)s [level=%(levelname)s]: docs-build: %(message)s"
logging.basicConfig(
    level=logging.getLevelName(os.environ.get("LOG_LEVEL", "INFO")),
    format=LOGGING_FORMAT,
)

DOCS_RTD_API_PROJECT_URL = os.environ.get("DOCS_RTD_API_PROJECT_URL")
if DOCS_RTD_API_PROJECT_URL is None:
    raise ValueError(
        "docs-build: RTD API Project URL not provided: "
        "Please set `DOCS_RTD_API_PROJECT_URL`"
    )

DOCS_RTD_API_TOKEN = os.environ.get("DOCS_RTD_API_TOKEN")
if DOCS_RTD_API_TOKEN is None:
    raise ValueError(
        "docs-build: RTD API Token not provided: "
        "Please set `DOCS_RTD_API_TOKEN`"
    )

DOCS_RTD_PROJECT_REF = os.environ.get("DOCS_RTD_PROJECT_REF", "latest")


def get_version_build_url(url: str, ref: str) -> str:
    """
    Tries to find the version in RTD given the reference

    :param url: The url to call to find versions
    :param ref: The ref to find
    :return: URL to the version build
    """
    headers = {"Authorization": f"Token {DOCS_RTD_API_TOKEN}"}
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code == 200:
        version_data = response.json()
        for result in version_data.get("results", []):
            if result.get("slug") == ref:
                return result.get("_links", {}).get("builds")

        next_url = version_data.get("next")
        if next_url:
            return get_version_build_url(next_url, ref)
    else:
        logging.error(
            "Failed to find versions to build for %s: [%s] %s",
            ref,
            response.status_code,
            response.text,
        )

    return None


def trigger_build(version_url: str) -> Tuple[str | None, str | None]:
    """
    Triggers an RTD build

    :param version_url: The specific version url to trigger
    :return: If successful, the two build URLs (API, and UI)
    """
    headers = {"Authorization": f"Token {DOCS_RTD_API_TOKEN}"}
    response = requests.post(version_url, headers=headers, timeout=10)
    if response.status_code == 202:
        build_data = response.json().get("build", {})
        return build_data.get("_links", {}).get("_self"), build_data.get(
            "urls", {}
        ).get("build")

    logging.error(
        "Failed to trigger build for %s: [%s] %s",
        version_url,
        response.status_code,
        response.text,
    )
    return None, None


def check_build_status(build_url: str) -> Tuple[bool, str]:
    """
    Checks the RTD build status

    :param build_url: The build url
    :return: Tuple with sucess status and error reason
    """
    headers = {"Authorization": f"Token {DOCS_RTD_API_TOKEN}"}
    while True:
        response = requests.get(build_url, headers=headers, timeout=10)
        if response.status_code == 200:
            build_info = response.json()
            state = build_info.get("state")
            if not state:
                return False, "Failed to get build state"

            status = state.get("code")
            if status in ["finished", "failed"]:
                return build_info.get("success", False), build_info.get(
                    "error"
                )

            logging.info("Waiting for build to finish ... %s", status)
            time.sleep(30)
        else:
            logging.error(
                "Failed to get build status: [%s] %s",
                response.status_code,
                response.text,
            )
            return False, response.text


if __name__ == "__main__":
    rtd_version_api_url = get_version_build_url(
        f"{DOCS_RTD_API_PROJECT_URL}/versions/", DOCS_RTD_PROJECT_REF
    )
    if not rtd_version_api_url:
        logging.error(
            "Failed to find versions to build with '%s'",
            DOCS_RTD_PROJECT_REF,
        )
        sys.exit(1)

    rtd_build_api_url, rtd_build_url = trigger_build(rtd_version_api_url)
    if not rtd_build_api_url:
        logging.error("Failed to trigger build with '%s'", rtd_build_api_url)
        sys.exit(1)

    logging.info("RTD build: %s", rtd_build_url)
    success, error = check_build_status(rtd_build_api_url)
    if not success:
        logging.error(
            "RTD build failed for '%s': %s", DOCS_RTD_PROJECT_REF, error
        )
        sys.exit(1)

    logging.info("RTD build successful for '%s'", DOCS_RTD_PROJECT_REF)
