# Titan AMR: Custom Industrial Warehouse Autonomous Mobile Robot

A complete, production-grade ROS 2 Humble autonomous mobile robot stack designed for industrial logistics, warehouse automation, SLAM, AMCL localization, Nav2 path planning, camera vision pipelines, and automated charging docking.

---

## 🛠 Package Architecture

```
ros2_ws/
├── src/
│   ├── custom_warehouse_robot_description/    # URDF, Xacro kinematics, sensors & meshes
│   ├── custom_warehouse_robot_gazebo/         # Warehouse world, charging dock & shelf models
│   ├── custom_warehouse_robot_navigation/     # SLAM, AMCL, Nav2 planners & maps
│   ├── custom_warehouse_robot_vision/         # OpenCV RGB-D pipeline & AI vision hooks
│   └── custom_warehouse_robot_autonomy/       # Auto-docking & shelf lifter controllers
```

---

## 🤖 1. Custom Robot Specifications ("Titan AMR")

- **Chassis**: Heavy-duty industrial AMR with chamfered safety bumpers, side skirts, and perimeter LED status halo.
- **Drive Configuration**: Differential drive with two high-torque drive wheels (160mm diameter) + 4-point stability caster suspension (zero tipping during heavy load acceleration).
- **Lifting Mechanism**: Active prismatic cargo lifter plate (+60mm vertical stroke) to hoist and transport warehouse shelf pods and EUR-pallets.
- **Sensory Suite**:
  - **360° Safety LiDAR**: High-frequency 2D laser scanner on an elevated turret (`/scan`).
  - **RGB-D Depth Camera**: Intel RealSense D435i style stereo depth camera publishing `/camera/rgb/image_raw`, `/camera/depth/image_raw`, and `/camera/depth/points`.
  - **6-DOF IMU**: Center-mounted inertial measurement unit (`/imu/data`).
  - **4x Corner Ultrasonic Sensors**: Blind-spot obstacle detection.
  - **Auto-Docking Contact Pads**: Dual rear gold-plated charging terminals with physical guidance funnels.

---

## 🏭 2. Warehouse Environment & Gazebo Simulation

- **Layout**: 20m x 16m enclosed logistics warehouse.
- **Features**:
  - Multiple pallet racking aisles with wide navigation clearance.
  - Heavy cargo crates and inspection barrels.
  - Movable storage shelf pods that Titan AMR can drive under and lift.
  - Dedicated **Auto-Docking & Charging Bay** equipped with physical alignment guide funnels and high-contrast visual fiducial targets for camera guidance.
- **Pre-mapped Occupancy Grid**: Includes high-resolution `warehouse_map.yaml` and `warehouse_map.pgm` (0.05 m/pixel).

---

## 🚀 3. Quick Start Guide

### Step 1: Install System Dependencies (one-time setup)
```bash
cd ~/ros2_ws
./install_dependencies.sh
```

### Step 2: Build Workspace
```bash
cd ~/ros2_ws
source /opt/ros/humble/setup.bash
colcon build --symlink-install
source install/setup.bash
```

---

## 🎯 4. Launching the Robot Stack

### Option A: Complete Warehouse Autonomous Bringup (Gazebo + RViz + AMCL + Nav2)
```bash
source install/setup.bash
ros2 launch custom_warehouse_robot_navigation warehouse_bringup.launch.py
```

### Option B: Run SLAM Mapping Mode (Create your own warehouse map)
```bash
source install/setup.bash
ros2 launch custom_warehouse_robot_navigation warehouse_bringup.launch.py slam:=true
```
To save the generated map after driving:
```bash
ros2 run nav2_map_server map_saver_cli -f ~/my_warehouse_map
```

### Option C: Robot Model Viewer (Inspect URDF joints in RViz)
```bash
source install/setup.bash
ros2 launch custom_warehouse_robot_description display.launch.py
```

---

## 👁️ 5. Vision Processing Pipeline & Future AI Tasks

Titan AMR includes a dedicated image vision package (`custom_warehouse_robot_vision`):
- **Live Topics**:
  - `/camera/rgb/image_raw`: Raw RGB color stream.
  - `/camera/depth/image_raw`: Metric depth map.
  - `/camera/depth/points`: 3D Point cloud.
  - `/vision/annotated_image`: HUD overlay with target acquisition, reticle, and FPS.
  - `/vision/docking_target`: 3D metric coordinates of the charging dock target.
- **AI Extension Hook**:
  - The node `vision_processor_node.py` contains `custom_vision_tasks_hook(frame)`, allowing drop-in integration of YOLOv8/v11 models, barcode/QR decoders, or defect detection.

---

## ⚡ 6. Auto-Docking & Multi-Function Capabilities

### Auto-Docking Service:
Initiate autonomous docking into the charging station:
```bash
ros2 service call /dock_robot std_srvs/srv/Trigger {}
```
Undock and resume operations:
```bash
ros2 service call /undock_robot std_srvs/srv/Trigger {}
```

### Shelf Lifter Mechanism:
Raise cargo plate:
```bash
ros2 service call /lifter/raise std_srvs/srv/Trigger {}
```
Lower cargo plate:
```bash
ros2 service call /lifter/lower std_srvs/srv/Trigger {}
```

### Run Full Autonomous Warehouse Mission:
Executes: Undock -> Drive to Aisle 1 -> Lift Shelf Pod -> Transport to Dispatch Staging -> Lower Shelf Pod -> Return to Dock -> Auto-Charge.
```bash
ros2 run custom_warehouse_robot_autonomy warehouse_mission
```
