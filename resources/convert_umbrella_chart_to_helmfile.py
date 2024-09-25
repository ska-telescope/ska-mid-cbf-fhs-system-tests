"""
This script converts an Helm umbrella chart into an helmfile
"""

import hashlib
import os
import shutil
from argparse import ArgumentParser
from urllib.parse import urlparse

import yaml

LIBRARY_CHARTS = ["ska-tango-util"]
VALUES_GO_TPL = '{{merge (.Values | get .Release.Name  dict)\
 (dict "global" (.Values | get "global"  dict)) |\
 toYaml}}'
CAR_HELM_REPO_URL = "https://artefact.skao.int/repository/helm-internal"


class LineBreakYamlDumper(yaml.SafeDumper):
    """
    LineBreakYamlDumper dumps yaml with a line break between
    top level keys
    """

    def write_line_break(self, data=None):
        """
        Breaks the line twice for top level keys
        """
        super().write_line_break(data)

        if len(self.indents) == 1:
            super().write_line_break()


def get_repository_name(url: str):
    """
    Gets a repository name given the url
    """
    if url.startswith("file://"):
        return None

    if url == CAR_HELM_REPO_URL:
        return "skatelescope"

    repo_md5 = hashlib.md5(url.encode("utf-8")).hexdigest()
    return f"{urlparse(url).netloc}.{repo_md5[:5]}"


def get_dependencies(chart_data):
    """
    Get the dependency names of a chart
    """
    return [
        dependency["name"]
        for dependency in chart_data.get("dependencies", [])
        if dependency["name"] not in LIBRARY_CHARTS
    ]


def get_dependency(chart_data, dependency):
    """
    Gets a dependency of a chart given its name
    """
    dependencies = chart_data.get("dependencies", [])
    for dep in dependencies:
        if dep["name"] == dependency:
            return dep

    return None


def generate_values_files(helmfile_dir, chart_values, dependencies):
    """
    Generates a global values file and a values file per dependency of a chart
    """
    with open(
        f"{os.path.join(helmfile_dir, 'values')}/global.values.yml",
        "w+",
        encoding="utf-8",
    ) as file:
        values = {}
        for value in chart_values:
            if value not in dependencies:
                values[value] = chart_values[value]

        if len(values.keys()) > 0:
            yaml.dump(values, file)

    for dependency in dependencies:
        with open(
            f"{os.path.join(helmfile_dir, 'values')}/{dependency}-values.yml",
            "w+",
            encoding="utf-8",
        ) as file:
            values = {}
            for value in chart_values:
                if value == dependency:
                    values[value] = chart_values[value]

            if len(values.keys()) > 0:
                yaml.dump(values, file)


def generate_helmfile(helmfile_dir, chart_data, dependencies):
    """
    Generates an helmfile using a environment-values post-processing pattern
    where the values are passed to the helmfile environment and loaded into
    the release. The post-processing strips the chart name and includes global
    variables
    """
    values_dir = os.path.join(".")
    environments_dir = os.path.join("..", "..", "environments")
    releases = []
    repositories = {}
    yaml_ext = (
        "yml"
        if os.path.exists(os.path.join(values_dir, "values.yml"))
        else "yaml"
    )
    environments = {
        "default": {
            "values": [
                os.path.join(values_dir, f"values.{yaml_ext}"),
                os.path.join(
                    environments_dir,
                    f"{{{{ .Environment.Name }}}}/values.{yaml_ext}",
                ),
            ]
        }
    }

    for dependency in dependencies:
        dependency_data = get_dependency(chart_data, dependency)
        if dependency_data is None:
            continue

        repository = get_repository_name(dependency_data["repository"])
        if repository is not None:
            chart = f"{repository}/{dependency}"
            repositories[repository] = dependency_data["repository"]
        else:
            chart = dependency_data["repository"].lstrip("file://")

        installed_tpl = '{{`{{ dig .Release.Name "enabled" true .Values }}`}}'
        releases.append(
            {
                "name": dependency,
                "chart": chart,
                "version": dependency_data["version"],
                "values": [
                    "values.gotmpl",
                ],
                "installedTemplate": installed_tpl,
            }
        )

    with open(
        os.path.join(helmfile_dir, "values.gotmpl"), "w+", encoding="utf-8"
    ) as file:
        file.write(VALUES_GO_TPL)

    with open(
        os.path.join(helmfile_dir, "helmfile.yaml"), "w+", encoding="utf-8"
    ) as file:
        yaml.dump_all(
            [
                {"environments": environments},
                {
                    "repositories": [
                        {"name": repo, "url": url}
                        for repo, url in repositories.items()
                    ],
                    "releases": releases,
                },
            ],
            file,
            sort_keys=False,
            Dumper=LineBreakYamlDumper,
        )


if __name__ == "__main__":
    parser = ArgumentParser(
        description="SKAO Helm Chart to helmfile conversion"
    )
    parser.add_argument(
        "-d",
        "--charts-dir",
        dest="charts_dir",
        default="./charts",
        required=False,
        help="Directory where the charts are held",
    )
    parser.add_argument(
        "-c",
        "--charts",
        nargs="+",
        dest="charts",
        required=True,
        help="List of charts in the charts directory to convert to helmfile",
    )

    args = parser.parse_args()
    for chart in args.charts:
        chart_path = os.path.join(args.charts_dir, chart)
        print(f"helmfile: Processing chart '{chart_path}'")
        if not os.path.exists(chart_path):
            raise ValueError(f"'{chart_path}' is not a valid chart directory")

        chart_file_path = os.path.join(chart_path, "Chart.yaml")
        if not os.path.exists(chart_file_path):
            raise ValueError(f"'{chart_file_path}' is not a valid chart file")

        with open(chart_file_path, "r", encoding="utf-8") as file:
            chart_data = yaml.safe_load(file)

        values_file_path = os.path.join(chart_path, "values.yaml")
        with open(values_file_path, "r", encoding="utf-8") as file:
            chart_values = yaml.safe_load(file)

        helmfile_dir = os.path.join(chart_path)
        files = ["helmfile.yaml", "values.gotmpl"]
        for file in [os.path.join(helmfile_dir, path) for path in files]:
            if os.path.exists(file):
                shutil.rmtree(file, ignore_errors=True)

        dependencies = get_dependencies(chart_data)
        generate_helmfile(helmfile_dir, chart_data, dependencies)
