from orchestration.controller import CodeHiveController, PROJECT_TYPES


if __name__ == "__main__":
    controller = CodeHiveController()

    print("Project types:")
    for index, project_type in enumerate(PROJECT_TYPES, 1):
        print(f"{index}. {project_type}")

    choice = input("Choose a project type [1]: ").strip() or "1"
    try:
        project_type = PROJECT_TYPES[int(choice) - 1]
    except (ValueError, IndexError):
        project_type = "General Python Project"

    user_input = input("Enter your request: ")
    result = controller.run(user_input, project_type=project_type)

    print("\nGenerated project folder:\n")
    print(result["project_dir"])
