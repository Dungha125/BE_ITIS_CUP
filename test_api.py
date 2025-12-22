"""
Script test API nhanh
Chạy: python test_api.py
"""
import requests
import json

BASE_URL = "http://localhost:8000/api"

def test_health():
    """Test health endpoint"""
    print("=" * 50)
    print("1. Testing Health Check")
    print("=" * 50)
    try:
        response = requests.get("http://localhost:8000/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        print("✅ Health check OK\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

def test_get_teams():
    """Test get teams endpoint"""
    print("=" * 50)
    print("2. Testing GET /api/tournament/teams")
    print("=" * 50)
    try:
        response = requests.get(f"{BASE_URL}/tournament/teams")
        print(f"Status: {response.status_code}")
        data = response.json()
        print(f"Success: {data.get('success')}")
        if data.get('success'):
            teams = data.get('data', {}).get('teams', [])
            print(f"Total teams: {len(teams)}")
            print(f"Confirmed: {data.get('data', {}).get('confirmed_count', 0)}/16")
        print("✅ Get teams OK\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

def test_register_team():
    """Test register team endpoint"""
    print("=" * 50)
    print("3. Testing POST /api/tournament/register")
    print("=" * 50)
    try:
        data = {
            "email": "test@example.com",
            "team_name": "Đội Test",
            "leader_name": "Nguyễn Văn A",
            "leader_student_id": "SV123456",
            "phone": "0123456789",
            "vice_leader_name": "Trần Thị B",
            "vice_leader_student_id": "SV123457",
            "vice_leader_phone": "0987654321",
            "members_list_text": "1. Nguyễn Văn A\n2. Trần Thị B\n3. Lê Văn C",
        }
        
        response = requests.post(
            f"{BASE_URL}/tournament/register",
            data=data
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        if result.get('success'):
            print(f"Order ID: {result.get('data', {}).get('order_id')}")
        print("✅ Register team OK\n")
        return result.get('data', {}).get('order_id') if result.get('success') else None
    except Exception as e:
        print(f"❌ Error: {e}\n")
        return None

def test_create_payment(order_id):
    """Test create payment endpoint"""
    if not order_id:
        print("⚠️  Skipping payment test (no order_id)")
        return
    
    print("=" * 50)
    print("4. Testing POST /api/tournament/create-payment")
    print("=" * 50)
    try:
        data = {"order_id": order_id}
        response = requests.post(
            f"{BASE_URL}/tournament/create-payment",
            json=data
        )
        print(f"Status: {response.status_code}")
        result = response.json()
        print(f"Success: {result.get('success')}")
        print(f"Message: {result.get('message')}")
        if result.get('success'):
            pay_data = result.get('data', {})
            print(f"Pay URL: {pay_data.get('pay_url', 'N/A')[:50]}...")
        print("✅ Create payment OK\n")
    except Exception as e:
        print(f"❌ Error: {e}\n")

if __name__ == "__main__":
    print("\n" + "=" * 50)
    print("🧪 TESTING ITISCUP TOURNAMENT API")
    print("=" * 50 + "\n")
    
    # Test các endpoints
    test_health()
    test_get_teams()
    order_id = test_register_team()
    test_create_payment(order_id)
    
    print("=" * 50)
    print("✅ Testing completed!")
    print("=" * 50)
    print("\n💡 Tips:")
    print("- Xem API docs tại: http://localhost:8000/docs")
    print("- Xem ReDoc tại: http://localhost:8000/redoc")
    print("- Server phải đang chạy: uvicorn app.main:app --reload")

