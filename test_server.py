import requests
import time

def test_server():
    try:
        response = requests.get('http://localhost:41005/')
        print(f"✅ Server is running! Status: {response.status_code}")
        print(f"Response: {response.json()}")
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to server on port 41005")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == '__main__':
    test_server()