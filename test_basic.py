import pytest
from unittest import mock
import subprocess
import os
import json
from datetime import time

# --- IMPORTANT: CHANGE 'assistant' below if your main file has a different name! ---
# We use a try/except to gracefully handle the case where the CI might have trouble 
# importing, although importing individual functions is usually safer.
try:
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
except ImportError as e:
    # If the import fails (e.g., missing dependencies), define placeholder functions 
    # to allow the tests focused on mocking to still run.
    print(f"Warning: Failed to import all functions from assistant.py: {e}")
    def speak(*args, **kwargs): pass 
    def ollama_response(*args, **kwargs): return {"content": "Mocked LLM failed to load."}
    # Define other placeholder functions as necessary if tests still rely on them.


# =========================================================
# 🐞🔫 FIX 1: Mocking Ollama API Calls (Bypasses Network)
# =========================================================

# Mocking the requests.post function globally for all LLM-related tests
@mock.patch('requests.post')
def test_ollama_response_works(mock_post):
    """
    Ensures that ollama_response can successfully handle a mocked 200 OK response
    and extracts the content correctly, bypassing the actual network call.
    """
    # Define the mock response object
    mock_response = mock.Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "message": {"content": "Mock LLM worked!"}
    }
    
    mock_post.return_value = mock_response
    
    # Call the function being tested
    response_message = ollama_response("test prompt")
    
    # Assertions
    mock_post.assert_called_once()
    assert "Mock LLM worked!" in response_message.get("content", "")

# =========================================================
# 🐞🔫 FIX 2: Mocking the Speak Function (Bypasses 'say')
# =========================================================

def test_speak_does_not_crash_ci(monkeypatch):
    """
    Mocks os.uname() and subprocess calls to prevent CI crash on the Mac 'say' command.
    Forces the code path to enter the subprocess block for correct mocking.
    """
    
    # Step 1: Define a class that mimics os.uname() but forces sysname to be 'Darwin'
    class MockUname:
        sysname = "Darwin"
        # The machine attribute is sometimes checked, so we include a safe value
        machine = "x86_64" 

    # Use monkeypatch to replace the actual os.uname function with our mock
    monkeypatch.setattr(os, 'uname', lambda: MockUname())
    
    # Step 2: Mock subprocess.Popen and subprocess.run to stop the execution
    with mock.patch('subprocess.Popen') as mock_popen, \
         mock.patch('subprocess.run') as mock_run:

        # Test non-blocking call
        speak("Testing non-blocking speech")
        mock_popen.assert_called_once()
        mock_run.assert_not_called()
        
        # Reset mocks for blocking call
        mock_popen.reset_mock()
        mock_run.reset_mock()
        
        # Test blocking call
        speak("Testing blocking speech", blocking=True)
        mock_run.assert_called_once()
        mock_popen.assert_not_called()

# =========================================================
# 🐞🔫 FIX 3: Testing Routine Management Logic (Core Features)
# =========================================================

def test_routine_management_logic_basic(monkeypatch):
    """
    Tests the core routine functions without hitting disk I/O.
    The goal is to test the internal logic, not the save/load mechanism.
    """
    
    # Mock disk I/O to prevent reading/writing to routine.json in CI
    mock_routine = []
    # Use monkeypatch to temporarily replace load_json and save_json
    monkeypatch.setattr('assistant.load_json', lambda x, y: mock_routine)
    
    def mock_save_json(filename, obj):
        mock_routine.clear()
        mock_routine.extend(obj)

    monkeypatch.setattr('assistant.save_json', mock_save_json)

    # 1. Test add_routine_entry
    result_add = add_routine_entry("09:00", "10:00", "daily meeting")
    assert "Success!" in result_add
    assert len(mock_routine) == 1
    
    result_add_2 = add_routine_entry("11:30", "12:30", "lunch")
    assert "Success!" in result_add_2
    assert len(mock_routine) == 2
    
    # 2. Test get_routine
    result_get = get_routine()
    assert "09:00 - 10:00: daily meeting" in result_get
    
    # 3. Test get_task_by_time
    result_task = get_task_by_time("09:30")
    assert "you should: daily meeting" in result_task
    
    # 4. Test remove_routine_entry
    result_remove = remove_routine_entry("meeting")
    assert "Successfully removed 1 routine entry" in result_remove
    assert len(mock_routine) == 1 # Only 'lunch' remains

    # 5. Test edge case (invalid time format)
    result_invalid = add_routine_entry("9-00", "10:00", "error test")
    assert "Error: Invalid time format" in result_invalid
    
    # 6. Test no activity found
    result_task_none = get_task_by_time("08:00")
    assert "No scheduled activity for this time." in result_task_none


# =========================================================
# 🐞🔫 FINAL TEST: Simple assert to ensure pytest runs
# =========================================================

def test_ci_final_runs():
    """A simple test to ensure the pytest framework is functional."""
    assert True
