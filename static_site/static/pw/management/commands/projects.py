import json
import os
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import TypedDict

from dateparser import parse
from django.core.management.base import BaseCommand, CommandError

OPEN_SOURCE = "Open Source"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")


class Project(TypedDict):
    last_updated: str
    name: str
    description: str
    stack: str
    company: str
    web_url: str
    github_url: str
    featured: bool
    active: bool
    private: bool


class Command(BaseCommand):
    help = "Manage projects with commands to update dates or add a new project from github."

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest="command", help="Sub-command help")

        update_parser = subparsers.add_parser(
            "update", help="Update project dates and sort them"
        )
        update_parser.set_defaults(func=self.update)

        add_parser = subparsers.add_parser("add", help="Add a new project")
        add_parser.add_argument("repo", type=str, help="Name of the GitHub project")
        add_parser.add_argument(
            "--dry-run", action="store_true", help="Simulate without saving"
        )
        add_parser.set_defaults(func=self.add)

    def handle(self, *args, **options):
        if options.get("func"):
            options["func"](options)
        else:
            self.print_help(prog_name="pw", subcommand="projects")

    def update(self, _):
        with edit_projects() as projects:
            need_update = [
                project
                for project in projects
                if project.get("active") and project.get("company") == OPEN_SOURCE
            ]
            updated_projects = []
            for project in need_update:
                repo_name = project["github_url"].replace("https://github.com/", "")
                commits = github_api_request(f"repos/{repo_name}/commits")
                last_update_date = commits[0]["commit"]["author"]["date"].split("T")[0]

                if project["last_updated"] != last_update_date:
                    project["last_updated"] = last_update_date
                    updated_projects.append(project["name"])
            projects.sort(key=lambda p: parse(p.get("last_updated")), reverse=True)
            projects.sort(key=lambda p: p.get("featured"), reverse=True)
            projects.sort(key=lambda p: p.get("priority", 0), reverse=True)

        if updated_projects:
            self.stdout.write(
                self.style.SUCCESS(
                    f"\nThe following projects were updated: {', '.join(updated_projects)}"
                )
            )
        else:
            self.stdout.write("No projects required updates.")

    def add(self, options):
        repo = options["repo"]
        dry_run = options["dry_run"]

        if "/" not in repo:
            user = github_api_request("user")
            repo = f"{user['login']}/{repo}"

        project_name = repo.split("/")[-1]

        try:
            github_project = github_api_request(f"repos/{repo}")
        except urllib.error.HTTPError as e:
            raise CommandError(f"Error fetching project: {e}")

        web_url = github_project.get("homepage") or input("Enter web URL: ").strip()
        featured = input("Is this project featured? (y/n): ").lower() == "y"
        stack = input("Enter stack: ").strip()
        company = input("Enter company (leave empty of OSS): ").strip() or OPEN_SOURCE

        project = {
            "last_updated": github_project["pushed_at"].split("T")[0],
            "name": project_name,
            "description": github_project.get("description", ""),
            "stack": stack,
            "company": company,
            "web_url": web_url or github_project["html_url"],
            "github_url": github_project["html_url"],
            "featured": featured,
            "active": True,
            "private": False,
        }

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry Run:"))
            self.stdout.write(json.dumps(project, indent=4))
            return

        with edit_projects() as projects:
            projects.append(project)

        self.stdout.write(
            self.style.SUCCESS(f"Project {project_name} added successfully.")
        )


@contextmanager
def edit_projects():
    # FIXME: find a simpler way to get the PROJECT_FILE_PATH
    from coltrane.config.settings import get_config
    from coltrane.config.paths import get_data_directory
    from coltrane.renderer import StaticRequest
    site = get_config(base_dir=Path(".")).get_site(StaticRequest(path="/"))
    projects_file = get_data_directory(site=site) / "projects.json"
    projects_file.touch(exist_ok=True)
    try:
        with open(projects_file) as file:
            projects = json.load(file)
        yield projects
    finally:
        projects_file.write_bytes(json.dumps(projects, indent=4).encode())


def github_api_request(path: str) -> dict:
    if not GITHUB_TOKEN:
        raise CommandError(
            "GitHub API token <GITHUB_TOKEN> is not set in the environment variables."
        )
    url = f"https://api.github.com/{path}"
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"}
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    return json.load(response)
