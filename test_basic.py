import json
import os
import pytest
from assistant import get_routine, get_task_by_time

# --- Setup Fixtures (Mock Data) ---

# Define the path to the routine file relative to where the test is run.
# Since the test is run from the project root after CD'ing into the nested folder,
# it should look for the file in the current directory (the nested folder).
# If the file is placed directly next to assistant.py and test_basic.py, 
# then the relative path is just "routine.json".

@pytest.fixture
def mock_routine_data():
    """Provides a sample routine structure for testing."""
    return [
        {"start": "09:00", "end": "10:00", "task": "Wake up and meditate"},
        {"start": "10:00", "end": "11:00", "task": "Breakfast and check emails"},
        {"start": "11:00", "end": "12:30", "task": "Morning walk or yoga"},
        {"start": "12:30", "end": "13:30", "task": "Lunch break"},
        {"start": "13:30", "end": "15:30", "task": "Work on personal project X"},
    ]

@pytest.fixture(autouse=True)
def mock_json_file(tmp_path, mock_routine_data):
    """Creates a temporary routine.json file for tests to use."""
    # This creates the file in the temporary directory used by pytest
    file_path = tmp_path / "routine.json"
    with open(file_path, "w") as f:
        json.dump(mock_routine_data, f, indent=4)
    
    # Temporarily set the environment variable to point assistant.py to this mock file
    original_path = os.environ.get('ROUTINE_FILE_PATH')
    # NOTE: You might need to adjust how your assistant.py reads the file path 
    # if it relies on a hardcoded path instead of an environment variable or relative path.
    # For this test structure to work, assistant.py should be designed to read the path
    # from a variable that can be mocked/set in the test environment.
    os.environ['ROUTINE_FILE_PATH'] = str(file_path)
    
    yield
    
    # Clean up and restore environment
    if original_path is not None:
        os.environ['ROUTINE_FILE_PATH'] = original_path
    else:
        del os.environ['ROUTINE_FILE_PATH']

# --- Test Cases ---

def test_get_routine_success():
    """Test that get_routine loads data successfully."""
    # Assuming get_routine loads the data using the mocked file path
    routine = get_routine(query=None, return_json=False)
    assert isinstance(routine, list)
    assert len(routine) > 0

def test_get_task_by_time_current_task(mocker):
    """Test finding a task currently in progress."""
    # Mock the current time to fall inside the 10:00-11:00 slot (e.g., 10:30)
    mocker.patch('assistant.now_dt', return_value='10:30') 
    
    result = get_task_by_time(query="10:30", return_json=False)
    assert "Breakfast and check emails" in result

def test_get_task_by_time_next_task(mocker):
    """Test finding the next task (your new feature)."""
    # Mock the current time to fall right before the next task (e.g., 10:59)
    mocker.patch('assistant.now_dt', return_value='10:59') 
    
    result = get_task_by_time(query="next", return_json=False)
    # The expected output should contain both current and next task info
    assert "Breakfast and check emails" in result
    assert "Morning walk or yoga" in result
    
def test_get_task_by_time_invalid_time():
    """Test handling of invalid time format."""
    result = get_task_by_time(query="4 PM", return_json=True)
    assert '"status": "error"' in result
    assert "Invalid time format" in result
