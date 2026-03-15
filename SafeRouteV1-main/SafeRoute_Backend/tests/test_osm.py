import requests
import json
import logging

def get_osm_data():
    urls = [
        "https://lz4.overpass-api.de/api/interpreter",
        "https://overpass.kumi.systems/api/interpreter",
        "https://overpass-api.de/api/interpreter"
    ]
    overpass_query = """
    [out:json][timeout:25];
    (
      way["highway"](17.4350,78.3400,17.4450,78.3550);
    );
    out body;
    >;
    out skel qt;
    """
    for overpass_url in urls:
        print(f"Trying {overpass_url}")
        try:
            response = requests.post(overpass_url, data={'data': overpass_query}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                with open("gachi_osm.json", "w") as f:
                    json.dump(data, f)
                print(f"Got {len(data.get('elements', []))} elements")
                return
            else:
                print(f"Status code {response.status_code}")
        except Exception as e:
            print(f"Failed: {e}")

if __name__ == "__main__":
    get_osm_data()
