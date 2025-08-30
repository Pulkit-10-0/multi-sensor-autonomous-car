# Vehicle Navigation and Control System
# Reads data from ESP32 sensors and controls autonomous navigation

import requests
import json
import time
import math
import threading
from dataclasses import dataclass
from typing import Optional, List, Tuple
import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

@dataclass
class SensorData:
    distance: float
    ir_status: str
    motion_status: str
    temperature: float
    humidity: float
    flame_status: str
    accel_x: float
    accel_y: float
    accel_z: float
    gyro_x: float
    gyro_y: float
    gyro_z: float
    autonomous_mode: bool

@dataclass
class Position:
    x: float
    y: float
    heading: float  # degrees

class VehicleController:
    def __init__(self, esp32_ip: str, map_file: str = "room_map.json"):
        self.esp32_ip = esp32_ip
        self.base_url = f"http://{esp32_ip}"
        self.map_file = map_file
        
        # Vehicle state
        self.current_position = Position(0, 0, 0)
        self.is_running = False
        self.manual_override = False
        
        # Navigation parameters
        self.safe_distance = 15.0  # cm
        self.turn_angle = 30  # degrees
        self.max_speed_threshold = 2.0  # m/s²
        
        # Environmental thresholds
        self.temp_min = 15.0  # °C
        self.temp_max = 35.0  # °C
        self.humidity_max = 80.0  # %
        
        # Map data
        self.room_bounds = None
        self.obstacles = []
        
        self.load_map()
        
    def load_map(self):
        """Load room map from JSON file"""
        try:
            with open(self.map_file, 'r') as f:
                map_data = json.load(f)
                self.room_bounds = map_data.get("room_bounds")
                self.obstacles = map_data.get("obstacles", [])
                logger.info(f"Map loaded: {len(self.obstacles)} obstacles")
        except FileNotFoundError:
            logger.warning(f"Map file {self.map_file} not found. Navigation will be limited.")
        except Exception as e:
            logger.error(f"Error loading map: {e}")
    
    def get_sensor_data(self) -> Optional[SensorData]:
        """Fetch sensor data from ESP32"""
        try:
            response = requests.get(f"{self.base_url}/data", timeout=3)
            if response.status_code == 200:
                data = response.json()
                
                # Parse accelerometer data
                accel_str = data.get('accel', 'X=0 Y=0 Z=0')
                accel_parts = accel_str.replace('X=', '').replace('Y=', '').replace('Z=', '').split()
                accel_x = float(accel_parts[0]) if len(accel_parts) > 0 else 0
                accel_y = float(accel_parts[1]) if len(accel_parts) > 1 else 0
                accel_z = float(accel_parts[2]) if len(accel_parts) > 2 else 0
                
                # Parse gyro data
                gyro_str = data.get('gyro', 'X=0 Y=0 Z=0')
                gyro_parts = gyro_str.replace('X=', '').replace('Y=', '').replace('Z=', '').split()
                gyro_x = float(gyro_parts[0]) if len(gyro_parts) > 0 else 0
                gyro_y = float(gyro_parts[1]) if len(gyro_parts) > 1 else 0
                gyro_z = float(gyro_parts[2]) if len(gyro_parts) > 2 else 0
                
                return SensorData(
                    distance=data.get('distance', 20.0),
                    ir_status=data.get('ir', 'Clear'),
                    motion_status=data.get('motion', 'No Motion'),
                    temperature=data.get('temperature', 25.0),
                    humidity=data.get('humidity', 50.0),
                    flame_status=data.get('flame', 'No Flame'),
                    accel_x=accel_x,
                    accel_y=accel_y,
                    accel_z=accel_z,
                    gyro_x=gyro_x,
                    gyro_y=gyro_y,
                    gyro_z=gyro_z,
                    autonomous_mode=data.get('autonomous', 'DISABLED') == 'ENABLED'
                )
        except Exception as e:
            logger.error(f"Error fetching sensor data: {e}")
            return None
    
    def send_command(self, command: str) -> bool:
        """Send movement command to ESP32"""
        try:
            response = requests.get(f"{self.base_url}/{command}", timeout=2)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error sending command {command}: {e}")
            return False
    
    def check_environmental_conditions(self, sensor_data: SensorData):
        """Monitor environmental conditions and alert on abnormalities"""
        
        # Temp check
        if sensor_data.temperature < self.temp_min or sensor_data.temperature > self.temp_max:
            logger.warning(f"ABNORMAL TEMPERATURE: {sensor_data.temperature}°C")
        
        # Humidity check
        if sensor_data.humidity > self.humidity_max:
            logger.warning(f"ABNORMAL HUMIDITY: {sensor_data.humidity}%")
        
        # Flame detection
        if "Flame Detected" in sensor_data.flame_status:
            logger.critical("FIRE DETECTED! Emergency stop!")
            self.send_command("stop")
            return False
        
        return True
    
    def check_vehicle_orientation(self, sensor_data: SensorData) -> bool:
        """Check if vehicle is upside down or moving too fast"""
        
        # Check if upside down (Z acceleration should be positive when upright)
        if sensor_data.accel_z < -5.0:
            logger.warning("VEHICLE MAY BE UPSIDE DOWN!")
            self.send_command("stop")
            return False
        
        # Check if tilted dangerously
        tilt_angle = math.degrees(math.atan2(sensor_data.accel_x, sensor_data.accel_z))
        if abs(tilt_angle) > 45:
            logger.warning(f"DANGEROUS TILT ANGLE: {tilt_angle:.1f}°")
        
        # Check for excessive speed (using acceleration magnitude)
        total_accel = math.sqrt(sensor_data.accel_x**2 + sensor_data.accel_y**2 + sensor_data.accel_z**2)
        if total_accel > self.max_speed_threshold:
            logger.warning(f"HIGH ACCELERATION DETECTED: {total_accel:.2f} m/s²")
        
        return True
    
    def check_intrusion(self, sensor_data: SensorData):
        """Check for motion detection (intruders)"""
        if "Motion Detected" in sensor_data.motion_status:
            logger.info("👥 MOTION DETECTED - Possible intruder")
    
    def obstacle_avoidance(self, sensor_data: SensorData) -> str:
        """Determine movement based on obstacle detection"""
        
        # Check ultrasonic sensor
        if sensor_data.distance < self.safe_distance:
            logger.info(f"Obstacle detected at {sensor_data.distance:.1f}cm - Turning")
            return "left" if time.time() % 2 < 1 else "right"  # Alternate turns
        
        # Check IR sensor
        if "Object Detected" in sensor_data.ir_status:
            logger.info("IR obstacle detected - Turning right")
            return "right"
        
        return "forward"
    
    def is_within_room_bounds(self, x: float, y: float) -> bool:
        """Check if position is within room boundaries"""
        if not self.room_bounds:
            return True  # No bounds defined, assume valid
        
        rb = self.room_bounds
        return (rb["x1"] <= x <= rb["x2"] and rb["y1"] <= y <= rb["y2"])
    
    def check_map_obstacles(self, x: float, y: float) -> bool:
        """Check if position conflicts with mapped obstacles"""
        for obstacle in self.obstacles:
            if (obstacle["x1"] <= x <= obstacle["x2"] and 
                obstacle["y1"] <= y <= obstacle["y2"]):
                return True  # Obstacle found
        return False
    
    def navigate_autonomously(self):
        """Main autonomous navigation loop"""
        turn_counter = 0
        max_turns = 8  # Prevent infinite turning
        
        while self.is_running:
            try:
                # Get sensor data
                sensor_data = self.get_sensor_data()
                if not sensor_data:
                    time.sleep(0.5)
                    continue
                
                # Check if manual override is active
                if not sensor_data.autonomous_mode:
                    logger.info("Manual override active - Stopping autonomous control")
                    self.manual_override = True
                    time.sleep(1)
                    continue
                else:
                    self.manual_override = False
                
                # Environmental and safety checks
                if not self.check_environmental_conditions(sensor_data):
                    time.sleep(2)
                    continue
                
                if not self.check_vehicle_orientation(sensor_data):
                    time.sleep(2)
                    continue
                
                # Check for intruders
                self.check_intrusion(sensor_data)
                
                # Determine movement
                movement = self.obstacle_avoidance(sensor_data)
                
                # Execute movement
                if movement == "forward":
                    turn_counter = 0
                    self.send_command("forward")
                    logger.info("Moving forward")
                elif movement in ["left", "right"]:
                    self.send_command(movement)
                    turn_counter += 1
                    logger.info(f"Turning {movement} (turn #{turn_counter})")
                    
                    # If stuck turning, try backing up
                    if turn_counter >= max_turns:
                        logger.info("Too many turns - Backing up")
                        self.send_command("backward")
                        time.sleep(1)
                        turn_counter = 0
                
                # Brief pause between commands
                time.sleep(0.3)
                
            except Exception as e:
                logger.error(f"Error in navigation loop: {e}")
                time.sleep(1)
    
    def start_navigation(self):
        """Start the autonomous navigation system"""
        if self.is_running:
            logger.info("Navigation already running")
            return
        
        self.is_running = True
        logger.info("Starting autonomous navigation...")
        
        # Start navigation in a separate thread
        nav_thread = threading.Thread(target=self.navigate_autonomously, daemon=True)
        nav_thread.start()
    
    def stop_navigation(self):
        """Stop the autonomous navigation system"""
        self.is_running = False
        self.send_command("stop")
        logger.info("Navigation stopped")
    
    def manual_control(self, command: str):
        """Send manual control commands"""
        if self.manual_override or not self.is_running:
            self.send_command(command)
            logger.info(f"Manual command: {command}")
        else:
            logger.warning("Cannot send manual commands while autonomous mode is active")

def main():
    # Configuration
    ESP32_IP = "192.168.1.100"  # Replace with your ESP32 IP
    MAP_FILE = "room_map.json"
    
    # Create controller
    controller = VehicleController(ESP32_IP, MAP_FILE)
    
    print("Control System")
    print("Commands: start, stop, forward, backward, left, right, status, quit")
    
    try:
        while True:
            command = input("\nEnter command: ").strip().lower()
            
            if command == "quit":
                break
            elif command == "start":
                controller.start_navigation()
            elif command == "stop":
                controller.stop_navigation()
            elif command in ["forward", "backward", "left", "right"]:
                controller.manual_control(command)
            elif command == "status":
                sensor_data = controller.get_sensor_data()
                if sensor_data:
                    print(f"Distance: {sensor_data.distance:.1f}cm")
                    print(f"IR: {sensor_data.ir_status}")
                    print(f"Motion: {sensor_data.motion_status}")
                    print(f"Temperature: {sensor_data.temperature:.1f}°C")
                    print(f"Humidity: {sensor_data.humidity:.1f}%")
                    print(f"Flame: {sensor_data.flame_status}")
                    print(f"Autonomous: {sensor_data.autonomous_mode}")
                else:
                    print("Failed to get sensor data")
            else:
                print("Unknown command")
    
    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        controller.stop_navigation()

if __name__ == "__main__":
    main()