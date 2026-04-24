#!/bin/bash

# Source the ROS2 workspace
source /opt/ros/jazzy/setup.bash
source ~/Damage_Road/install/setup.bash

echo "Starting Road Inspector System..."

# Start Camera Node
ros2 run road_inspector camera_node &
echo "Launched: Camera Node"

# Start AI Node
ros2 run road_inspector ai_node &
echo "Launched: AI Node (YOLOv8)"

# Start GUI Node
ros2 run road_inspector gui_node &
echo "Launched: GUI Dashboard"

# Start Navigation Node
ros2 run road_inspector navigation_node &
echo "Launched: Navigation Logic"

ros2 run road_inspector check_camera &
echo "Launched: Camera Check Node"

# Keep the script alive and wait for Ctrl+C
echo "System is running. Press [CTRL+C] to stop all nodes."
trap "kill 0" EXIT
wait
