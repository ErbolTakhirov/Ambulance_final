
import requests
import time

def test_osrm():
    start_lat, start_lng = 42.875144, 74.562028
    end_lat, end_lng = 42.8755, 74.6030
    
    coords = f"{start_lng},{start_lat};{end_lng},{end_lat}"
    
    servers = [
        "http://router.project-osrm.org/route/v1/driving",
        "https://routing.openstreetmap.de/routed-car/route/v1/driving"
    ]
    
    headers = {
        'User-Agent': 'AmbulanceRouteOptimizer/1.0 (Educational Project)'
    }
    
    print("Testing OSRM connection...")
    
    for base_url in servers:
        url = f"{base_url}/{coords}"
        print(f"\nTrying server: {base_url}")
        try:
            start_time = time.time()
            response = requests.get(url, headers=headers, timeout=20)
            elapsed = time.time() - start_time
            
            print(f"Status Code: {response.status_code}")
            print(f"Time: {elapsed:.2f}s")
            
            if response.status_code == 200:
                data = response.json()
                routes = data.get('routes', [])
                print(f"Success! Found {len(routes)} routes.")
                return True
            else:
                print(f"Error: {response.text}")
                
        except Exception as e:
            print(f"Exception: {e}")

    print("\nAll servers failed.")
    return False

if __name__ == "__main__":
    test_osrm()
