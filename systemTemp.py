#!/usr/bin/env python3

import subprocess
import json

def run_sensors():
    try:
        output = subprocess.check_output(['sensors', '-f'], text=True)
        return output
    except subprocess.CalledProcessError:
        return None

def parse_sensors_output(output):
    sensors_data = {}
    current_sensor = None

    lines = output.split('\n')
    for idx, line in enumerate(lines):
        if line and line.strip().startswith('Adapter:'):
            current_sensor = lines[idx-1].strip().replace('-', '_')
            sensors_data[current_sensor] = {}
        elif current_sensor and '°F' in line:
            parts = line.strip().split(':')
            sensor_name = parts[0].strip()
            value = parts[1].split('°F')[0].strip()
            try:
                value = float(value)
                sensors_data[current_sensor][sensor_name] = value
            except ValueError:
                print(f"Warning: Unable to convert value to float in line '{line}'")

    return sensors_data

def generate_prtg_json(sensors_data):
    prtg_json = {"prtg": {"result": []}}

    for sensor, data in sensors_data.items():
        for sensor_name, value in data.items():
            prtg_json["prtg"]["result"].append({
                "channel": f"{sensor}_{sensor_name}",
                "value": value,
                "unit": "Custom",
                "customunit": "°F",
                "float": 1
            })

    return json.dumps(prtg_json)

if __name__ == "__main__":
    sensors_output = run_sensors()
    if sensors_output:
        sensors_data = parse_sensors_output(sensors_output)
        if sensors_data:
            prtg_json = generate_prtg_json(sensors_data)
            print(prtg_json)
        else:
            print("Error: No valid sensor data found.")
    else:
        print("Error: Unable to fetch sensors data.")
