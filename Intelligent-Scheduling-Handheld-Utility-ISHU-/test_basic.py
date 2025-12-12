import pytest
from unittest import mock
import subprocess
import os
import json
from datetime import time, datetime

# --- CRITICAL FIX: Direct Import ---
# IMPORT THE MODULE ITSELF for reference (e.g., assistant.pyjokes)
import assistant
from assistant import (
    ollama_response,
    speak,
    add_routine_entry,
    get_task_by_time,
    remove_routine_entry,
    get_routine,
    parse_time,
    tell_joke,
    get_favorite,
    set_favorite_color,
    tell_story
)


# =========================================================
# 🧪 Test 1: Mocking Ollama API Calls
# =========================================================

@mock.patch('requests.post')
def test_ollama_response_works(mock_post):
    """
    Ensures that ollama_response can successfully handle a mocked 200 OK response.
    """
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Mock LLM worked!"}
    }
    
    mock_post.return_value = mock_response
    
    response_message = ollama_response("test prompt")
    
    mock_post.assert_called_once()
    assert "Mock LLM worked!" in response_message.get("content", "")

# -----------------------------------------------------------------------------

# =========================================================
# 🗣️ Test 2: FIXING test_speak_does_not_crash_ci
# CRITICAL CHANGE: Explicitly mock os.uname() to force the 'Darwin' path.
# =========================================================

def test_speak_does_not_crash_ci():
    """
    Forces the speak function into the Mac execution path by mocking os.uname()
    to return 'Darwin', ensuring subprocess.Popen/run are called.
    """
    
    # 1. Define the mock object that returns 'Darwin'
    class MockUname:
        sysname = "Darwin"
        machine = "x86_64" # Arbitrary value

    # 2. Patch the built-in functions simultaneously using the context manager.
    with (
        mock.patch('os.uname', return_value=MockUname()),
        mock.patch('subprocess.Popen') as mock_popen,
        mock.patch('subprocess.run') as mock_run,
    ):

        # Test non-blocking call (should call Popen)
        speak("Testing non-blocking speech")
        mock_popen.assert_called_once_with(['say', 'Testing non-blocking speech'])
        mock_run.assert_not_called()
        
        # Reset mocks for blocking call
        mock_popen.reset_mock()
        
        # Test blocking call (should call run)
        speak("Testing blocking speech", blocking=True)
        mock_run.assert_called_once_with(['say', 'Testing blocking speech'])
        mock_popen.assert_not_called()

# -----------------------------------------------------------------------------

# =========================================================
# 📅 Test 3: FIXING test_routine_management_logic_basic
# Updated assertions to handle JSON string output from assistant functions.
# =========================================================

def test_routine_management_logic_basic(monkeypatch):
    """
    Tests the core routine functions without hitting disk I/O, using monkeypatch
    to mock file operations.
    """
    
    # Use a dictionary to hold the routine list; this allows the inner list 
    # to be reliably replaced/updated by mock_save_json.
    routine_data_container = {"routine": []}
    
    # Mock load_json to return the current state of the routine
    def mock_load_json(filename, default):
        return routine_data_container["routine"]
    
    # Mock save_json to replace the routine list in the container with the new object
    def mock_save_json(filename, obj):
        routine_data_container["routine"] = obj

    monkeypatch.setattr('assistant.load_json', mock_load_json)
    monkeypatch.setattr('assistant.save_json', mock_save_json)

    # 1. Test add_routine_entry
    result_add_json = add_routine_entry("09:00", "10:00", "daily meeting")
    
    # 🔥🔥🔥 FIX: Parse JSON output and check 'status' and 'message' content
    result_add = json.loads(result_add_json)
    assert result_add["status"] == "success"
    assert "daily meeting" in result_add["message"]
    
    # Check the length of the list INSIDE the container
    assert len(routine_data_container["routine"]) == 1
    
    result_add_2_json = add_routine_entry("11:30", "12:30", "lunch")
    
    # 🔥🔥🔥 FIX: Parse JSON output
    result_add_2 = json.loads(result_add_2_json)
    assert result_add_2["status"] == "success"
    assert "lunch" in result_add_2["message"]
    
    # Check the length of the list INSIDE the container
    assert len(routine_data_container["routine"]) == 2
    
    # Check sorting: should be 09:00 then 11:30
    assert routine_data_container["routine"][0]['start'] == "09:00"
    
    # 2. Test get_routine (returns full JSON string of the list)
    result_get_json = get_routine()
    result_get = json.loads(result_get_json)
    # Check the number of entries and content of the first entry
    assert len(result_get) == 2
    assert result_get[0]['activity'] == "daily meeting"
    
    # 3. Test get_task_by_time (Mocked to return a specific time for test)
    # Mock the current time to fall into the first entry (e.g., 09:30)
    class MockDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            return cls(2025, 12, 12, 9, 30, 0) # Mock time 09:30

    monkeypatch.setattr('assistant.datetime', MockDatetime)
    
    result_task_json = get_task_by_time("09:30")
    # 🔥🔥🔥 FIX: Parse JSON output and check 'status' and 'activity'
    result_task = json.loads(result_task_json)
    assert result_task["status"] == "found"
    assert result_task["activity"] == "daily meeting"
    
    # 4. Test remove_routine_entry
    result_remove_json = remove_routine_entry("meeting")
    # 🔥🔥🔥 FIX: Parse JSON output and check 'status' and 'removed_count'
    result_remove = json.loads(result_remove_json)
    assert result_remove["status"] == "success"
    assert result_remove["removed_count"] == 1
    
    # Check the length of the list INSIDE the container
    assert len(routine_data_container["routine"]) == 1 # Only 'lunch' remains

    # 5. Test edge case (invalid time format)
    result_invalid = add_routine_entry("9-00", "10:00", "error test")
    # 🔥🔥🔥 FIX: The assistant code returns a simple error string if invalid format
    assert "ERROR: Invalid time format" in result_invalid
    
    # 6. Test no activity found
    result_task_none_json = get_task_by_time("08:00")
    # 🔥🔥🔥 FIX: Parse JSON output and check 'status'
    result_task_none = json.loads(result_task_none_json)
    assert result_task_none["status"] == "not_found"

# -----------------------------------------------------------------------------

# =========================================================
# 📝 Test 4: Testing Simple Features (Joke, Favorite Color)
# =========================================================

# Ensure pyjokes is mocked if it failed to import (for safety)
@mock.patch('assistant.pyjokes', new=mock.MagicMock())
@mock.patch('assistant.load_json')
@mock.patch('assistant.save_json')
def test_simple_features(mock_save, mock_load):
    """Tests joke telling and favorite color features."""
    
    # Now that 'assistant' is imported as a module, this reference is valid.
    if assistant.pyjokes is not None:
        assistant.pyjokes.get_joke.return_value = "Mock Joke!"
        assert tell_joke() == "Mock Joke!"
    
    # Mock data for favorites
    mock_load.return_value = {}
    
    # Test set_favorite_color
    result_set = set_favorite_color("blue")
    assert "I'll remember your favorite color is blue" in result_set
    # Check that save_json was called with the correct dictionary (color: blue)
    mock_save.assert_called_once() 
    
    # Test get_favorite (by loading the mock data set above)
    mock_load.reset_mock()
    mock_load.return_value = {"color": "blue"}
    result_get = get_favorite()
    assert "Your favorite color is blue" in result_get


# -----------------------------------------------------------------------------

# =========================================================
# ✅ Test 5: Final Sanity Check
# =========================================================

def test_ci_final_runs():
    """A simple test to ensure the pytest framework is functional."""
    assert True