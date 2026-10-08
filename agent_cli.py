import argparse
import asyncio
import itertools
import sys
from pathlib import Path

from app.services.agent import AgentService
from app.services.ollama import OllamaService
from app.services.project import ProjectService


async def run_agent(message: str, project_path: str | None):
    project_service = ProjectService(load_config=False)
    result = project_service.set_project(project_path or str(Path.cwd()))
    if not result["success"]:
        print(result["error"])
        return

    if project_service.project_root is None:
        print("No project selected. Launch the agent inside a project folder or use --project.")
        return

    agent = AgentService(project_service, OllamaService())
    history = []
    print(f"Project: {project_service.project_root}")
    print("Enter a coding request. The agent will analyze it and ask for confirmation before editing.")

    if message:
        await handle_prompt(agent, message, history)
        return

    print("Coding agent ready. Type 'exit' to quit.")
    while True:
        try:
            prompt = input("agent> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return

        if prompt.lower() in {"exit", "quit"}:
            return
        if prompt:
            await handle_prompt(agent, prompt, history)


async def handle_prompt(agent, prompt, history):
    print("\nAnalyzing your request...")
    plan = await process_with_progress(agent, prompt, history, planning=True)
    print("\nThe agent plans to:")
    print(format_plan(plan))
    print("  (No files have been changed.)")
    print()

    try:
        confirmation = input("Proceed with this plan? [y/N]: ").strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        return

    if confirmation != "y":
        print("Cancelled. No files were changed.\n")
        return

    print("\nImplementing approved plan...")
    result = await process_with_progress(agent, prompt, history, plan=plan, planning=False)
    display_result(result)
    history.extend([
        {"role": "user", "content": prompt},
        {"role": "assistant", "content": result.get("message", "")}
    ])


async def process_with_progress(agent, prompt, history=None, plan=None, planning=False):
    progress_messages = []

    def report(message):
        progress_messages.append(message)

    if planning:
        task = asyncio.create_task(agent.plan(prompt, history=history, on_progress=report))
    else:
        task = asyncio.create_task(agent.process(prompt, history=history, plan=plan, on_progress=report))
    spinner = itertools.cycle("|/-\\")
    last_message_count = 0

    while not task.done():
        while last_message_count < len(progress_messages):
            print(f"\r{' ' * 100}\r[agent] {progress_messages[last_message_count]}", flush=True)
            last_message_count += 1
        print(f"\r[agent] Working {next(spinner)}", end="", flush=True)
        await asyncio.sleep(0.4)

    while last_message_count < len(progress_messages):
        print(f"\r{' ' * 100}\r[agent] {progress_messages[last_message_count]}", flush=True)
        last_message_count += 1

    print(f"\r{' ' * 100}\r", end="", flush=True)
    return await task


def format_plan(plan):
    lines = []
    in_code_block = False
    for raw_line in (plan or "").splitlines():
        line = raw_line.strip()
        if line.startswith("```"):
            in_code_block = not in_code_block
            continue
        if in_code_block or not line:
            continue
        if line.startswith(("1.", "2.", "3.", "4.", "-", "*")):
            line = line.lstrip("-* ").strip()
            if len(line) > 2 and line[0].isdigit() and line[1] == ".":
                line = line[2:].strip()
            if any(marker in line for marker in ("{", "}", "=", "=>", "def ", "class ", "import ")):
                continue
            lines.append(f"  - {line}")
        if len(lines) == 4:
            break
    return "\n".join(lines) or "  - Review the request and apply the necessary project changes."


def display_result(result):
    print("\nImplementation:")
    if result.get("changes"):
        for change in result["changes"]:
            print(f"  - {change}")
    else:
        print("  - No file changes reported")
    print("\nCode review:")
    print(result.get("message") or "The agent returned no review.")
    print()


def main():
    parser = argparse.ArgumentParser(description="Local Coding AI command-line agent")
    parser.add_argument("message", nargs="?", help="One request to run, then exit")
    parser.add_argument("--project", help="Project directory; defaults to the current folder")
    args = parser.parse_args()
    asyncio.run(run_agent(args.message, args.project))


if __name__ == "__main__":
    main()
