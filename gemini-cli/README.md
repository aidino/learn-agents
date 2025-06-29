# Gemini CLI tutorial

## Quickstart

1. Prerequisites: Ensure you have Node.js version 18 or higher installed.
2. Run the CLI: Execute the following command in your terminal:

```bash
npx https://github.com/google-gemini/gemini-cli
```

Or install it with:

```bash
npm install -g @google/gemini-cli
gemini
```

## User Case Study

### Scenario

A developer is tasked with implementing a new feature in a large, unfamiliar codebase. The feature requires interacting with a complex internal API that is poorly documented.

### How Gemini CLI helps

1.  **Code Comprehension:** The developer uses Gemini CLI to search the codebase for examples of how the internal API is used.
    *   **Example:** The developer runs `search_file_content(pattern='InternalAPI.call')` to find all instances where the `InternalAPI` is used.

2.  **API Understanding:** By reading the existing code, the developer gains a better understanding of the API's functionality and how to use it correctly.
    *   **Example:** After finding a relevant file from the search, the developer uses `read_file(absolute_path='/path/to/relevant/file.js')` to examine the code and understand the API's parameters and return values.

3.  **Implementation:** The developer implements the new feature, using the knowledge gained from the codebase to guide their work.
    *   **Example:** The developer uses `write_file` to create a new file with the feature implementation, or `replace` to add the new code to an existing file, following the patterns they observed.

4.  **Testing:** The developer uses Gemini CLI to find existing tests for the API, and uses them as a template for writing new tests for the new feature.
    *   **Example:** The developer runs `glob(pattern='**/*test.js')` to find all test files, then reads a relevant test file to understand the testing structure. They then create a new test file for their feature.

### Outcome

The developer is able to implement the new feature quickly and correctly, despite the lack of documentation. The new feature is well-tested and integrates seamlessly with the existing codebase.

## Prompt Examples

### List files in the current directory
`list_directory(path='.')`

### Run a shell command
`run_shell_command(command='ls -l')`

### Find all python files in the project
`glob(pattern='**/*.py')`

### Search for a specific function in the codebase
`search_file_content(pattern='def my_function')`

### Read the content of a file
`read_file(absolute_path='/path/to/your/file.py')`

### Write a new file
`write_file(file_path='/path/to/your/new_file.py', content='print("Hello, World!")')`

### Replace a string in a file
`replace(file_path='/path/to/your/file.py', old_string='print("Hello, World!")', new_string='print("Hello, Gemini!")')`