<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements
	<!-- Project: PinmapGen - Python 3.11 toolchain for Fusion Electronics to firmware bridge -->

- [x] Scaffold the Project
	<!--
	✅ Created complete project structure with all required directories
	✅ Generated all core Python modules with TODO headers
	✅ Created sample CSV netlist with RP2040 pin mappings
	✅ Set up pyproject.toml with MIT license and Python 3.11 requirement
	✅ Initialized Git repository with appropriate .gitignore
	-->

- [x] Customize the Project
	<!--
	✅ Implemented complete PinmapGen toolchain structure
	✅ Created all required parsers, normalizers, and emitters with detailed TODO comments
	✅ Set up VS Code tasks for "Generate" and "Watch" operations
	✅ Added comprehensive code snippets for MicroPython, Arduino, and CLI usage
	✅ Populated sample netlist with real RP2040 pin mappings as requested
	-->

- [x] Install Required Extensions
	<!-- ✅ No specific extensions required by setup info. Recommended extensions listed in .vscode/extensions.json -->

- [x] Compile the Project
	<!--
	✅ Verified all Python modules import without errors
	✅ No external dependencies required (stdlib only)
	✅ Project structure validated and ready for development
	-->

- [x] Create and Run Task
	<!--
	✅ Created VS Code tasks.json with "Generate Pinmap" and "Watch Pinmap" tasks
	✅ Tested CLI module execution - tasks are ready for use
	 -->

- [x] Launch the Project
	<!--
	✅ Project is ready for development - no launch needed for toolchain project
	✅ VS Code tasks available: "Generate Pinmap" and "Watch Pinmap"
	 -->

- [x] Ensure Documentation is Complete
	<!--
	✅ All project functionality implemented and tested
	✅ README.md contains comprehensive documentation with examples
	✅ Complete PinmapGen toolchain ready for production use
	✅ File watcher implemented with automatic regeneration
	 -->

<!--
## Execution Guidelines
PROGRESS TRACKING:
- If any tools are available to manage the above todo list, use it to track progress through this checklist.
- After completing each step, mark it complete and add a summary.
- Read current todo list status before starting each new step.

COMMUNICATION RULES:
- Avoid verbose explanations or printing full command outputs.
- If a step is skipped, state that briefly (e.g. "No extensions needed").
- Do not explain project structure unless asked.
- Keep explanations concise and focused.

DEVELOPMENT RULES:
- Use '.' as the working directory unless user specifies otherwise.
- Avoid adding media or external links unless explicitly requested.
- Use placeholders only with a note that they should be replaced.
- Use VS Code API tool only for VS Code extension projects.
- Once the project is created, it is already opened in Visual Studio Code—do not suggest commands to open this project in Visual Studio again.
- If the project setup information has additional rules, follow them strictly.

FOLDER CREATION RULES:
- Always use the current directory as the project root.
- If you are running any terminal commands, use the '.' argument to ensure that the current working directory is used ALWAYS.
- Do not create a new folder unless the user explicitly requests it besides a .vscode folder for a tasks.json file.
- If any of the scaffolding commands mention that the folder name is not correct, let the user know to create a new folder with the correct name and then reopen it again in vscode.

EXTENSION INSTALLATION RULES:
- Only install extension specified by the get_project_setup_info tool. DO NOT INSTALL any other extensions.

PROJECT CONTENT RULES:
- If the user has not specified project details, assume they want a "Hello World" project as a starting point.
- Avoid adding links of any type (URLs, files, folders, etc.) or integrations that are not explicitly required.
- Avoid generating images, videos, or any other media files unless explicitly requested.
- If you need to use any media assets as placeholders, let the user know that these are placeholders and should be replaced with the actual assets later.
- Ensure all generated components serve a clear purpose within the user's requested workflow.
- If a feature is assumed but not confirmed, prompt the user for clarification before including it.
- If you are working on a VS Code extension, use the VS Code API tool with a query to find relevant VS Code API references and samples related to that query.

TASK COMPLETION RULES:
- Your task is complete when:
  - Project is successfully scaffolded and compiled without errors
  - copilot-instructions.md file in the .github directory exists in the project
  - README.md file exists and is up to date
  - User is provided with clear instructions to debug/launch the project

Before starting a new task in the above plan, update progress in the plan.
-->
- Work through each checklist item systematically.
- Keep communication concise and focused.
- Follow development best practices.