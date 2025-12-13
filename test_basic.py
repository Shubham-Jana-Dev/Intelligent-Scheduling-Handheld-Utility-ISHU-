import json
import os
import pytest
import datetime
# Import the function parse_time to use the real logic for comparison
from assistant import get_routine, get_task_by_time, ROUTINE_FILE_PATH, parse_time 

# --- Setup Fixtures (Mock Data) ---

@pytest.fixture
def mock_routine_data():
    """Provides a sample routine structure for testing. Keys changed to 'activity'."""
    return [
        {"start": "09:00", "end": "10:00", "activity": "Wake up and meditate"}, 
        {"start": "10:00", "end": "11:00", "activity": "Breakfast and check emails"},
        {"start": "11:00", "end": "12:30", "activity": "Morning walk or yoga"}, 
        {"start": "12:30", "end": "13:30", "activity": "Lunch break"}, 
        {"start": "13:30", "end": "15:30", "activity": "Work on personal project X"}, 
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
    
    mock_now_dt = datetime.datetime.combine(datetime.date.today(), datetime.time(10, 30))
    
    # FIX: Create a mock object that wraps datetime, then configure its methods.
    # This prevents the TypeError when trying to patch an immutable attribute.
    mock_datetime = mocker.MagicMock(wraps=datetime)
    mock_datetime.now.return_value = mock_now_dt
    mock_datetime.today.return_value = mock_now_dt.date() # Ensure today() returns a date object
    mock_datetime.date.today.return_value = mock_now_dt.date() # For safety if .date() is accessed
    
    # Patch the entire datetime object in assistant.py
    mocker.patch('assistant.datetime', mock_datetime)

    # get_task_by_time() with no argument uses the mocked current time (10:30)
    result = get_task_by_time() 
    result_data = json.loads(result)
    
    assert result_data["status"] == "found"
    assert "Breakfast and check emails" in result_data["activity"]


def test_get_task_by_time_next_task(mocker):
    """Test finding a task by explicit time, and a next task."""
    
    # --- Test 1: Querying a time *inside* an activity ---
    # No mocking is needed here because query_time is provided
    result_in_task = get_task_by_time(query_time="10:00") 
    result_data_in_task = json.loads(result_in_task)
    
    assert result_data_in_task["status"] == "found"
    assert "Breakfast and check emails" in result_data_in_task["activity"]
    
    # --- Test 2: Querying a time *between* activities (to find the next one) ---
    
    mock_today_date = datetime.date(2025, 12, 13) # Arbitrary fixed date
    
    # FIX: Patch the entire datetime object in assistant.py for explicit query time.
    # This ensures datetime.combine(datetime.today().date(), ...) works correctly.
    mock_datetime = mocker.MagicMock(wraps=datetime)
    mock_datetime.today.return_value = mock_today_date
    mock_datetime.date.today.return_value = mock_today_date # For safety

    mocker.patch('assistant.datetime', mock_datetime)
    
    result_gap = get_task_by_time(query_time="15:35")
    result_data_gap = json.loads(result_gap)
    
    # Assertion checks for the routine wrap-around logic
    assert result_data_gap["status"] == "next_found"
    assert "Wake up and meditate" in result_data_gap["activity"] 


def test_get_task_by_time_invalid_time():
    """Test handling of invalid time format."""
    # get_task_by_time() takes 'query_time' as a string argument
    result = get_task_by_time(query_time="4 PM") 
    assert '"status": "error"' in result
    assert "Invalid time format" in result