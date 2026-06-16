from brain.patch_writer import generate_patch, apply_patch
from brain.error_analyzer import analyze_error
from brain.retest_controller import run_with_retries
from sandbox.executor import run_command
from sandbox.workspace_tools import read_dependency_file
from sandbox.workspace_tools import analyze_file_extensions
from sandbox.workspace_tools import detect_project_type
from brain.model_manager import (
    get_current_model,
    set_current_model,
    get_supported_models
)
from brain.openrouter_client import chat as openrouter_chat
from brain.tool_router import choose_tool

from sandbox.workspace_tools import (
    list_workspace_files,
    read_workspace_file,
    create_workspace_file,
    scan_workspace,
    project_summary,
    scan_folder
)

from sandbox.file_guard import is_trusted


print("🤖 Agent Started")
print(f"🧠 Model Mode: {get_current_model()}")
print("Type 'exit' to quit.\n")


while True:

    task = input("👤 You: ").strip()

    # EXIT
    if task.lower() == "exit":
        print("🤖 Agent: Goodbye")
        break

    # SHOW MODE
    if task.lower() == "/mode":
        print("\n🤖 Agent:")
        print("🧠 Current Mode:", get_current_model())
        continue

    # CHANGE MODE
    if task.lower().startswith("/mode "):
        parts = task.split()

        if len(parts) == 2:
            new_mode = parts[1]

            if set_current_model(new_mode):
                print("\n🤖 Agent:")
                print("✅ Model changed to", get_current_model())
            else:
                print("\n🤖 Agent:")
                print("❌ Unsupported model")
                print("Available modes:")
                for model in get_supported_models():
                    print("-", model)

        continue

    # TOOL ROUTING
    tool = choose_tool(task)

    if tool == "list_files":

        files = list_workspace_files()

        print("\n🤖 Agent:")
        print("📂 Workspace Files")
        for file in files:
            print("-", file)

    elif tool == "read_file":

        filename = task.replace("read ", "", 1).strip()

        print("\n🤖 Agent:")
        print(read_workspace_file(filename))

    elif tool == "create_file":

        filename = task.replace("create ", "", 1).strip()

        print("\n🤖 Agent:")
        print(create_workspace_file(filename, "Created by Agent"))

    elif tool == "scan_workspace":

        files = scan_workspace()

        print("\n🤖 Agent:")
        print("📂 Workspace Scan")
        for file in files:
            print("-", file)

    elif tool == "project_summary":

        summary = project_summary()

        print("\n🤖 Agent:")
        print("📊 Project Summary")
        print(f"Total Files : {summary['total_files']}")
        print(f"Python Files: {summary['python_files']}")
        print(f"Text Files  : {summary['text_files']}")
    elif tool == "scan_folder":

        folder_path = task.replace("scan ", "", 1).strip()

        check = is_trusted(folder_path)

        if not check["trusted"]:
            print("\n🤖 Agent:")
            print("❌ Access Denied:", check["reason"])
            continue

        files = scan_folder(folder_path)

        print("\n🤖 Agent:")
        print("📂 Folder Scan Result:")
        for file in files:
            print("-", file)

        # ✅ Auto Detect Project Type
        project_type = detect_project_type(folder_path)

        # ✅ Extension Analysis
        extensions = analyze_file_extensions(folder_path)

        if extensions:
            print("\n📊 File Extensions Found:")
            for ext, count in extensions.items():
                print(f"{ext} : {count}")

    elif tool == "detect_project":
        folder_path = task.replace("detect ", "", 1).strip()

        check = is_trusted(folder_path)

        if not check["trusted"]:
            print("\n🤖 Agent:")
            print("❌ Access Denied:", check["reason"])
            continue

        project_type = detect_project_type(folder_path)

        print("\n🤖 Agent:")
        print("🧩 Project Type Detected:")
        print(project_type)
    elif tool == "dependencies":

        folder_path = task.replace("dependencies ", "", 1).strip()

        check = is_trusted(folder_path)

        if not check["trusted"]:
            print("\n🤖 Agent:")
            print("❌ Access Denied:", check["reason"])
            continue

        deps = read_dependency_file(folder_path)

        print("\n📦 Dependencies:")
        print(deps)

    elif tool == "run_command":

        command = task.replace("run ", "", 1).strip()

        print("\n🤖 Agent:")
        print("⚙ Running:", command)

        result = run_with_retries(command)

        if result["success"]:
            print("\n✅ Success after", result["attempts"], "attempt(s)")
            print(result.get("output", ""))
            continue

        # ---- FAILURE START ----
        print("\n❌ Failed after", result["attempts"], "attempt(s)")

        error_text = result.get("error")

        print("\n⚠ Raw Error:")
        print(error_text)

        print("\n🧠 AI Analysis:")
        analysis = analyze_error(command, error_text)
        print(analysis)

        if not analysis or "FIX_TYPE:" not in analysis:
            continue

        fix_type = analysis.split("FIX_TYPE:")[-1].split("\n")[0].strip()

        # =========================
        # COMMAND FIX
        # =========================
        if fix_type == "COMMAND":

            if "FIX_ACTION:" not in analysis:
                continue

            fix_line = analysis.split("FIX_ACTION:")[-1].strip().split("\n")[0].strip()

            if fix_line == "NONE" or fix_line == "":
                continue

            print("\n🔧 Proposed Fix:", fix_line)
            confirm = input("Apply fix? (y/n): ").strip().lower()

            if confirm == "y":

                print("\n⚙ Applying fix...")
                fix_result = run_with_retries(fix_line)

                if fix_result["success"]:
                    print("✅ Fix applied. Retesting...\n")

                    retest = run_with_retries(command)

                    if retest["success"]:
                        print("✅ Issue resolved.")
                        print(retest.get("output", ""))
                    else:
                        print("❌ Still failing after fix.")
                else:
                    print("❌ Fix command failed.")

        # =========================
        # PATCH FIX
        # =========================
        elif fix_type == "PATCH":

            if "FIX_ACTION:" not in analysis:
                continue

            fix_action = analysis.split("FIX_ACTION:")[-1].strip()

            print("\n🛠 Patch Required:")
            print(fix_action)

            confirm = input("Generate and apply patch? (y/n): ").strip().lower()

            if confirm == "y":

                target_file = input("Enter file path to patch: ").strip()

                new_content = generate_patch(target_file, fix_action)

                success, message = apply_patch(target_file, new_content)

                if success:
                    print("✅ Patch applied. Retesting...\n")

                    retest = run_with_retries(command)

                    if retest["success"]:
                        print("✅ Issue resolved.")
                        print(retest.get("output", ""))
                    else:
                        print("❌ Still failing after patch.")
                else:
                    print("❌ Patch failed:", message)

        # ---- FAILURE END ----

    elif tool == "autofix_project":

        folder_path = task.replace("autofix ", "", 1).strip()

        check = is_trusted(folder_path)
        if not check["trusted"]:
            print("❌ Access Denied:", check["reason"])
            continue

        print("\n🔍 Detecting project type...")
        project_type = detect_project_type(folder_path)
        print("🧩 Project Type:", project_type)

        # ===== NODE PROJECT =====
        if "Node" in project_type or "React" in project_type:

            print("\n📦 Installing dependencies...")
            install_result = run_with_retries("npm install", cwd=folder_path)

            if not install_result["success"]:
                print("❌ npm install failed.")
                continue

            print("✅ Dependencies installed.")

            attempts = 0
            max_attempts = 3

            while attempts < max_attempts:

                print("\n🚀 Attempting to start project...")
                result = run_with_retries("npm run dev", cwd=folder_path)

                if result["success"]:
                    print("✅ Project started successfully.")
                    print(result.get("output", ""))
                    break

                print("❌ Start failed.")
                error_text = result.get("error")

                print("\n🧠 Analyzing error...")
                analysis = analyze_error("npm run dev", error_text)
                print(analysis)

                if "FIX_TYPE:" not in analysis:
                    break

                fix_type = analysis.split("FIX_TYPE:")[-1].split("\n")[0].strip()

                if fix_type == "COMMAND" and "FIX_ACTION:" in analysis:

                    fix_line = analysis.split("FIX_ACTION:")[-1].strip().split("\n")[0].strip()

                    if fix_line not in ["NONE", ""]:
                        print("\n🔧 Applying suggested fix:", fix_line)
                        fix_result = run_with_retries(fix_line, cwd=folder_path)

                        if not fix_result["success"]:
                            print("❌ Fix failed.")
                            break

                else:
                    print("⚠ Patch-type fixes not automated in autofix mode yet.")
                    break

                attempts += 1

            if attempts == max_attempts:
                print("❌ Autofix reached max attempts.")

        else:
            print("⚠ Autofix currently supports Node/React projects only.")

    else:
        # No tool matched → send straight to the AI for a streamed response
        print("\n🤖 Agent:")
        try:
            openrouter_chat(task)
        except RuntimeError as e:
            print(f"⚠ AI Error: {e}")