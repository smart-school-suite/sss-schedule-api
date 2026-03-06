"""
Mock Validation Script
Tests all request mocks against the Pydantic schema
"""
import json
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.schemas import SchedulingRequest, SchedulingResponse

def test_request_mock(file_path: str) -> tuple[bool, str]:
    """Test a request mock file against the schema"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate against schema
        request = SchedulingRequest(**data)
        return True, f"✅ {Path(file_path).name} is valid"
    except Exception as e:
        return False, f"❌ {Path(file_path).name} failed: {str(e)[:100]}"

def test_response_mock(file_path: str) -> tuple[bool, str]:
    """Test a response mock file against the schema"""
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Validate against schema
        response = SchedulingResponse(**data)
        return True, f"✅ {Path(file_path).name} is valid"
    except Exception as e:
        return False, f"❌ {Path(file_path).name} failed: {str(e)[:100]}"

def main():
    print("=" * 60)
    print("MOCK VALIDATION TEST")
    print("=" * 60)
    
    # Request mocks
    request_mocks = [
        "mocks/requests/minimal_valid.json",
        "mocks/requests/break_period_mock.json",
        "mocks/requests/soft_constraints_mock.json",
        "mocks/requests/required_joint_periods_mock.json",
    ]
    
    print("\n📥 REQUEST MOCKS:")
    print("-" * 60)
    request_results = []
    for mock in request_mocks:
        success, message = test_request_mock(mock)
        request_results.append(success)
        print(message)
    
    # Response mocks
    response_mocks = [
        "mocks/response/optimal.response.example.json",
        "mocks/response/partial.response.example.json",
        "mocks/response/error.response.example.json",
    ]
    
    print("\n📤 RESPONSE MOCKS:")
    print("-" * 60)
    response_results = []
    for mock in response_mocks:
        success, message = test_response_mock(mock)
        response_results.append(success)
        print(message)
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    total_tests = len(request_results) + len(response_results)
    passed_tests = sum(request_results) + sum(response_results)
    
    print(f"Total Tests: {total_tests}")
    print(f"Passed: {passed_tests}")
    print(f"Failed: {total_tests - passed_tests}")
    
    if passed_tests == total_tests:
        print("\n🎉 ALL MOCKS VALID! Implementation matches perfectly.")
        return 0
    else:
        print("\n⚠️  Some mocks failed validation. See details above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
