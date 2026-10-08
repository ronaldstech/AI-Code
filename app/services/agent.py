import json


class AgentService:

    def __init__(self, project_service, ollama_service):
        self.project_service = project_service
        self.ollama_service = ollama_service

    async def plan(self, message: str, history=None, on_progress=None):
        messages = self._conversation(
            "You are the planning phase of a coding agent. Analyze the request and, "
            "when needed, inspect the selected project using only read_file and search_project. "
            "Do not modify files and do not output source code, code blocks, or code snippets. "
            "End with no more than four short numbered action statements describing what will "
            "be changed and how it will be checked. Ground every action in the user's request; "
            "name the target file type, requested values, and expected result when provided. "
            "Never say only 'review the request' or 'apply necessary changes'.",
            history,
            message
        )
        read_tools = [tool for tool in self._tools() if tool["function"]["name"] in {"read_file", "search_project"}]
        for step in range(4):
            if on_progress:
                on_progress(f"Analyzing request (step {step + 1})...")
            response = await self.ollama_service.chat(messages, tools=read_tools)
            assistant_message = response.get("message", {})
            tool_calls = assistant_message.get("tool_calls", [])
            if not tool_calls:
                fallback_call = self._parse_fallback_tool_call(assistant_message.get("content", ""))
                if fallback_call and fallback_call["function"]["name"] in {"read_file", "search_project"}:
                    tool_calls = [fallback_call]
            if not tool_calls:
                return self._plan_response(
                    assistant_message.get("content", ""), message
                )
            messages.append(assistant_message)
            for tool_call in tool_calls:
                name = tool_call.get("function", {}).get("name")
                arguments = tool_call.get("function", {}).get("arguments", {})
                if on_progress:
                    on_progress(f"Analyzing with {name}...")
                result = self._run_tool(name, arguments)
                messages.append({"role": "tool", "content": json.dumps(result), "name": name})
        return self._plan_response("", message)

    def _plan_response(self, content, request):
        cleaned = self._clean_response(content)
        generic = {
            "I could not understand that tool request, so no files were changed.",
            "The agent returned an empty response."
        }
        vague_markers = (
            "review the request",
            "necessary changes",
            "apply necessary",
            "appropriate files"
        )
        if cleaned not in generic and not any(marker in cleaned.lower() for marker in vague_markers):
            return cleaned

        return (
            "1. Inspect the files related to this request.\n"
            f"2. Implement the requested outcome: {request.strip()}\n"
            "3. Run focused checks to verify the result."
        )

    async def process(self, message: str, history=None, plan=None, on_progress=None):
        if self.project_service.project_root is None:
            return {
                "message": "Select a project before asking the coding agent to edit files.",
                "model": None,
                "changes": []
            }

        messages = self._conversation(
            "You are a coding agent. Inspect files before changing them. Use the provided "
            "tools to read, create, modify, and delete files. Only work inside the selected "
            "project. The user approved the plan supplied with this request. You must use the "
            "write_file or delete_file tools when the request requires changes; do not merely "
            "describe code in your response. Use real paths relative to the project root; never "
            "use placeholders such as path/to/file.ext. After completing the work, summarize "
            "changes and validation.",
            history,
            f"Approved plan:\n{plan}\n\nUser request:\n{message}" if plan else message
        )

        tools = self._tools()
        changes = []
        executed_calls = set()
        for step in range(8):
            if on_progress:
                on_progress(f"Thinking (step {step + 1})...")
            response = await self.ollama_service.chat(messages, tools=tools)
            assistant_message = response.get("message", {})
            tool_calls = assistant_message.get("tool_calls", [])

            if not tool_calls:
                fallback_call = self._parse_fallback_tool_call(
                    assistant_message.get("content", "")
                )
                if fallback_call is not None:
                    tool_calls = [fallback_call]

            if not tool_calls:
                return {
                    "message": self._clean_response(
                        assistant_message.get("content", "")
                    ),
                    "model": response.get("model"),
                    "changes": changes
                }

            messages.append(assistant_message)
            for tool_call in tool_calls:
                name = tool_call.get("function", {}).get("name")
                arguments = tool_call.get("function", {}).get("arguments", {})
                if on_progress:
                    progress_arguments = arguments
                    if isinstance(progress_arguments, str):
                        try:
                            progress_arguments = json.loads(progress_arguments)
                        except json.JSONDecodeError:
                            progress_arguments = {}
                    if not isinstance(progress_arguments, dict):
                        progress_arguments = {}
                    path = progress_arguments.get("path", progress_arguments.get("query", ""))
                    on_progress(f"Running {name}{f' ({path})' if path else ''}...")
                call_key = json.dumps(
                    {"name": name, "arguments": arguments}, sort_keys=True
                )
                if call_key in executed_calls:
                    if changes:
                        return {
                            "message": "The requested file changes were completed. "
                                       "The model repeated the same operation afterward, "
                                       "so it was stopped safely.",
                            "model": response.get("model"),
                            "changes": changes
                        }
                    return {
                        "message": "The agent repeated the same file operation, so it was stopped. "
                                   "No further changes were made.",
                        "model": response.get("model"),
                        "changes": changes
                    }
                executed_calls.add(call_key)
                result = self._run_tool(name, arguments)
                if name in {"write_file", "delete_file"} and result.get("success"):
                    action = "created/updated" if name == "write_file" else "deleted"
                    changes.append(f"{action} {result.get('path', arguments.get('path'))}")
                messages.append({
                    "role": "tool",
                    "content": json.dumps(result),
                    "name": name
                })

        return {
            "message": "The agent reached its tool-call limit before finishing.",
            "model": None,
            "changes": changes
        }

    def _conversation(self, system_prompt, history, message):
        messages = [{"role": "system", "content": system_prompt}]
        if history:
            messages.extend(history[-12:])
        messages.append({"role": "user", "content": message})
        return messages

    def _parse_fallback_tool_call(self, content):
        if not isinstance(content, str):
            return None

        call = self._parse_json_object(content)
        if call is None:
            return None

        if not isinstance(call, dict) or "name" not in call:
            return None

        known_tools = {tool["function"]["name"] for tool in self._tools()}
        if call["name"] not in known_tools:
            return None

        return {
            "function": {
                "name": call["name"],
                "arguments": call.get("arguments") or {}
            }
        }

    def _parse_json_object(self, content):
        text = content.strip()
        if text.startswith("```"):
            lines = text.splitlines()
            text = "\n".join(line for line in lines if not line.strip().startswith("```"))

        try:
            value, _ = json.JSONDecoder().raw_decode(text)
            return value
        except json.JSONDecodeError:
            start = text.find("{")
            if start == -1:
                return None
            try:
                value, _ = json.JSONDecoder().raw_decode(text[start:])
                return value
            except json.JSONDecodeError:
                return None

    def _clean_response(self, content):
        if not isinstance(content, str):
            return "The agent returned an empty response."

        call = self._parse_json_object(content)
        if call is None:
            return content

        if not isinstance(call, dict) or "name" not in call:
            return content

        if str(call["name"]).lower() in {"hi", "hello", "hey"}:
            return "Hello! I am ready to inspect and modify the selected project."

        return "I could not understand that tool request, so no files were changed."

    def _run_tool(self, name, arguments):
        try:
            if isinstance(arguments, str):
                arguments = json.loads(arguments)

            if name == "read_file":
                content = self.project_service.read_file(arguments["path"])
                return {"success": content is not None, "content": content}
            if name == "write_file":
                return self.project_service.write_file(
                    arguments["path"], arguments["content"]
                )
            if name == "delete_file":
                return self.project_service.delete_file(arguments["path"])
            if name == "search_project":
                return {"success": True, "results": self.project_service.search(arguments["query"])}
            return {"success": False, "error": "Unknown tool"}
        except (KeyError, TypeError, json.JSONDecodeError) as error:
            return {"success": False, "error": f"Invalid tool arguments: {error}"}

    def _tools(self):
        return [
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read a UTF-8 file in the selected project.",
                    "parameters": {
                        "type": "object",
                        "required": ["path"],
                        "properties": {"path": {"type": "string"}}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Create or replace a UTF-8 file in the selected project.",
                    "parameters": {
                        "type": "object",
                        "required": ["path", "content"],
                        "properties": {
                            "path": {"type": "string"},
                            "content": {"type": "string"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_file",
                    "description": "Delete an existing file in the selected project.",
                    "parameters": {
                        "type": "object",
                        "required": ["path"],
                        "properties": {"path": {"type": "string"}}
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_project",
                    "description": "Search text across files in the selected project.",
                    "parameters": {
                        "type": "object",
                        "required": ["query"],
                        "properties": {"query": {"type": "string"}}
                    }
                }
            }
        ]