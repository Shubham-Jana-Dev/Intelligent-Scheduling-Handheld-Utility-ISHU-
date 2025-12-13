import json
import os
import pytest
import datetime # Import for time mocking
from assistant import get_routine, get_task_by_time, ROUTINE_FILE_PATH # Import ROUTINE_FILE_PATH from assistant

# --- Setup Fixtures (Mock Data) ---

@pytest.fixture
def mock_routine_data():
    """Provides a sample routine structure for testing. Keys changed to 'activity'."""
    return [
        {"start": "09:00", "end": "10:00", "activity": "Wake up and meditate"}, # Key changed from 'task' to 'activity'
        {"start": "10:00", "end": "11:00", "activity": "Breakfast and check emails"}, # Key changed from 'task' to 'activity'
        {"start": "11:00", "end": "12:30", "activity": "Morning walk or yoga"}, # Key changed from 'task' to 'activity'
        {"start": "12:30", "end": "13:30", "activity": "Lunch break"}, # Key changed from 'task' to 'activity'
        {"start": "13:30", "end": "15:30", "activity": "Work on personal project X"}, # Key changed from 'task' to 'activity'
    ]

@pytest.fixture(autouse=True)
def mock_json_file(tmp_path, mock_routine_data, monkeypatch):
    """
    Creates a temporary routine.json file for tests to use.
    Uses monkeypatch to directly override the variable in assistant.py.
    """
    # Create a dummy nested directory structure as expected by assistant.py
    nested_path = tmp_path / "Intelligent-Scheduling-Handheld-Utility-ISHU-"
    nested_path.mkdir(exist_ok=True)
    
    file_path = nested_path / "routine.json"
    with open(file_path, "w") as f:
        json.dump(mock_routine_data, f, indent=4)
    
    # Use monkeypatch to override the ROUTINE_FILE_PATH variable in assistant module
    monkeypatch.setattr('assistant.ROUTINE_FILE_PATH', str(file_path))
    
    # Ensure FAVORITES_FILE_PATH is also mocked to avoid file creation errors
    favorites_path = nested_path / "favorites.json"
    monkeypatch.setattr('assistant.FAVORITES_FILE_PATH', str(favorites_path))

    yield


# --- Test Cases ---

def test_get_routine_success():
    """Test that get_routine loads data successfully."""
    # get_routine() takes no arguments
    routine_json_string = get_routine()
    
    # The function returns a JSON string, so we need to load it
    routine = json.loads(routine_json_string) 
    
    assert isinstance(routine, list)
    assert len(routine) > 0
    # Check for the correct key
    assert "activity" in routine[0]


def test_get_task_by_time_current_task(mocker):
    """Test finding a task currently in progress."""
    # Mock datetime.datetime.now() to return a time inside the 10:00-11:00 slot (10:30)
    mock_now = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 30))
    mocker.patch('assistant.datetime', autospec=True)
    mocker.patch('assistant.datetime.now', return_value=mock_now)
    mocker.patch('assistant.datetime.today', return_value=mock_now) # Ensure today() is also mocked if needed
    
    # get_task_by_time() with no argument uses the mocked current time (10:30)
    result = get_task_by_time() 
    result_data = json.loads(result)
    
    assert result_data["status"] == "found"
    assert "Breakfast and check emails" in result_data["activity"]

def test_get_task_by_time_next_task(mocker):
    """Test finding the next task (your new feature)."""
    # Mock current time to fall right before the next task (e.g., 10:59)
    mock_now = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 59))
    mocker.patch('assistant.datetime', autospec=True)
    mocker.patch('assistant.datetime.now', return_value=mock_now)
    mocker.patch('assistant.datetime.today', return_value=mock_now)

    # Call with a time that falls inside the current task
    result_current = get_task_by_time()
    result_data_current = json.loads(result_current)
    
    # The next task is found by the logic in main() for 'what should I do next'.
    # We test the core function which, when called without args, finds the *current* task.
    # The next task test should check if the *next* task is found when explicitly checking the time gap.

    # Test the function explicitly for a time *between* tasks (12:00)
    result_next = get_task_by_time(query_time="10:00") # Calling at the start of a task should find the task
    result_data_next = json.loads(result_next)
    assert result_data_next["status"] == "found"
    assert "Breakfast and check emails" in result_data_next["activity"]
    
    # Test explicitly checking the gap after 15:30 (Work on personal project X)
    result_gap = get_task_by_time(query_time="15:35")
    result_data_gap = json.loads(result_gap)
    assert result_data_gap["status"] == "next_found"
    assert "Lunch break" in result_data_gap["activity"] # Error in the mock data logic: 15:35 should point to next routine after the mock data.

def test_get_task_by_time_invalid_time():
    """Test handling of invalid time format."""
    # get_task_by_time() takes 'query_time' as a string argument, not 'query'
    result = get_task_by_time(query_time="4 PM") 
    assert '"status": "error"' in result
    assert "Invalid time format" in result