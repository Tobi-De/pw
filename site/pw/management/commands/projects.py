import json
import os
from pathlib import Path
from typing import TypedDict

from django.core.management.base import BaseCommand, CommandError
import urllib.request
from coltrane.config.paths import get_data_directory

# Path to the projects file
PROJECT_FILE_PATH = get_data_directory() / "projects.json"
OPEN_SOURCE = "Open Source"
GH_API_TOKEN = os.getenv("GITHUB_TOKEN")

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

        update_parser = subparsers.add_parser("update-dates", help="Update project dates")
        update_parser.set_defaults(func=self.update_dates)

        add_parser = subparsers.add_parser("add-project", help="Add a new project")
        add_parser.add_argument("repo", type=str, help="Name of the GitHub project")
        add_parser.add_argument("--dry-run", action="store_true", help="Simulate without saving")
        add_parser.set_defaults(func=self.add_project)

    def handle(self, *args, **options):
        if options.get("func"):
            options["func"](options)
        else:
            self.stdout.write(f"Please provide a valid command, available options are: add-project, update-dates")

    def update_dates(self, _):
        if not PROJECT_FILE_PATH.exists():
            raise CommandError(f"{PROJECT_FILE_PATH} does not exist.")

        with open(PROJECT_FILE_PATH) as file:
            projects: list[Project] = json.load(file)

        need_update = [
            project for project in projects if project.get("active") and project.get("company") == OPEN_SOURCE
        ]
        updated_projects = []
        for project in need_update:
            repo_name = project["github_url"].replace("https://github.com/", "")
            commits = github_api_request(f"repos/{repo_name}/commits")
            last_update_date = commits[0]["commit"]["author"]["date"].split("T")[0]

            if project["last_updated"] != last_update_date:
                project["last_updated"] = last_update_date
                updated_projects.append(project["name"])

        with open(PROJECT_FILE_PATH, "w") as file:
            json.dump(projects, file, indent=4)
        
        if updated_projects:
            self.stdout.write(self.style.SUCCESS(f"\nThe following projects were updated: {', '.join(updated_projects)}"))
        else:
            self.stdout.write("No projects required updates.")

    def add_project(self, options):
        repo = options["repo"]
        dry_run = options["dry_run"]

        project_name = repo.split("/")[-1]

        try:
            github_project = github_api_request(f"repos/{repo}")
        except urllib.error.HTTPError as e:
            raise CommandError(f"Error fetching project: {e}")

        web_url = github_project.get("homepage") or input("Enter web URL: ").strip()
        featured = input("Is this project featured? (y/n): ").lower() == "y"
        stack = input("Enter stack: ").strip()

        project = {
            "last_updated": github_project["pushed_at"].split("T")[0],
            "name": project_name,
            "description": github_project.get("description", ""),
            "stack": stack,
            "company": OPEN_SOURCE,
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

        if not PROJECT_FILE_PATH.exists():
            raise CommandError(f"{PROJECT_FILE_PATH} does not exist.")

        with open(PROJECT_FILE_PATH, "r") as file:
            projects = json.load(file)

        projects.append(project)

        with open(PROJECT_FILE_PATH, "w") as file:
            json.dump(projects, file, indent=4)

        self.stdout.write(self.style.SUCCESS(f"Project {project_name} added successfully."))



def github_api_request(path: str) -> dict:
    if not GH_API_TOKEN:
        raise CommandError("GitHub API token <GITHUB_TOKEN> is not set in the environment variables.")
    url = f"https://api.github.com/{path}"
    headers = {"Authorization": f"Bearer {GH_API_TOKEN}"}
    request = urllib.request.Request(url, headers=headers)
    response = urllib.request.urlopen(request)
    return json.load(response)
