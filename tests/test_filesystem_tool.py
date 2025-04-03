import pytest
from pathlib import Path
import os # Import os module
# Adjust the import path based on your project structure
from tools.filesystem_tool import read_file, write_file, list_directory, OUTPUT_DIR

# Fixture to ensure the output directory exists and is clean before/after tests
@pytest.fixture(autouse=True)
def manage_output_dir():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yield # Run the test
    # Clean up test files (optional)
    for item in OUTPUT_DIR.glob("test_*"):
        if item.is_file():
            item.unlink()
        elif item.is_dir():
            # Be careful with recursive deletion in tests!
            # shutil.rmtree(item)
            pass

def test_write_and_read_file():
    """Test writing to a file and reading it back."""
    file_path = "test_write_read.txt"
    content = "Hello from the test!"
    write_input = f"{file_path}|{content}"

    write_result = write_file(write_input)
    assert "Successfully wrote" in write_result
    assert file_path in write_result # Check if the correct path is reported

    # Verify file exists
    full_path = OUTPUT_DIR / file_path
    assert full_path.exists()
    assert full_path.is_file()

    # Test reading
    read_result = read_file(file_path)
    assert read_result == content

def test_list_directory():
    """Test listing the output directory."""
    # Create some test files/dirs first
    (OUTPUT_DIR / "test_list_file1.txt").touch()
    (OUTPUT_DIR / "test_list_subdir").mkdir(exist_ok=True)
    (OUTPUT_DIR / "test_list_subdir" / "test_list_file2.txt").touch()

    list_result_root = list_directory(".") # List root of outputs
    assert "test_list_file1.txt (FILE)" in list_result_root
    assert "test_list_subdir (DIR)" in list_result_root

    list_result_subdir = list_directory("test_list_subdir") # List subdir
    assert "test_list_file2.txt (FILE)" in list_result_subdir

def test_path_security_write():
    """Test that writing outside the allowed directory is prevented."""
    # Attempt path traversal
    write_result_trav = write_file("../test_outside.txt|Attempt to write outside")
    assert "Error: Invalid or disallowed file path" in write_result_trav
    assert not Path("../test_outside.txt").exists()

    # Attempt absolute path
    # Note: Absolute path check might behave differently on Windows/Linux
    # Let's try writing to system root (should definitely fail)
    # Adapt path if needed for Windows, e.g., C:/test_abs.txt
    # write_result_abs = write_file("/test_abs.txt|Attempt absolute write")
    # assert "Error: Invalid or disallowed file path" in write_result_abs

def test_path_security_read():
    """Test reading outside the allowed directory."""
    read_result_trav = read_file("../some_other_file.txt")
    assert "Error: Invalid or disallowed file path" in read_result_trav

    # read_result_abs = read_file("/etc/passwd") # Example absolute path
    # assert "Error: Invalid or disallowed file path" in read_result_abs


# Add more tests for other tools (browser, terminal - careful with terminal tests!, reporting)
# For terminal, mock subprocess.run or only test very safe commands like 'echo'.
# For browser, consider mocking playwright or testing against local static HTML files.