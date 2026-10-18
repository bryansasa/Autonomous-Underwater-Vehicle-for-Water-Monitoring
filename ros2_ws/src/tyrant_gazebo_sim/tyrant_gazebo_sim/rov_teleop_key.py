# -*- coding: utf-8 -*-
"""
Teleoperation Keyboard Sederhana untuk Mengendalikan ROV di Gazebo / Simulasi
Menerbitkan perintah kecepatan Twist ke topik /cmd_vel:
- W / S : Naik / Turun (Heave)
- I / K : Maju / Mundur (Surge)
- J / L : Putar Kiri / Kanan (Yaw)
- U / O : Geser Kiri / Kanan (Sway)
- Spasi : Berhenti seketika
"""

import sys
import select
import termios
import tty
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist

INSTRUCTIONS = """
========================================================
  KONTROL MANUAL TELEOP ROV TYRANT-AQ (BAB 4 SIMULASI)
========================================================
  [W] : Naik ke Permukaan (Heave +)
  [S] : Menyelam ke Dasar (Heave -) [Uji Anoksia]
  [I] : Maju (Surge +)
  [K] : Mundur (Surge -)
  [J] : Putar Kiri (Yaw +)
  [L] : Putar Kanan (Yaw -)
  [U] : Geser Kiri (Sway -)
  [O] : Geser Kanan (Sway +)
  [Spasi] : Stop (Netral)
  [CTRL+C]: Keluar
========================================================
"""


def get_key(settings):
    if sys.platform == 'win32':
        import msvcrt
        if msvcrt.kbhit():
            return msvcrt.getch().decode('utf-8', errors='ignore')
        return ''
    else:
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.1)
        if rlist:
            key = sys.stdin.read(1)
        else:
            key = ''
        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        return key


def main():
    settings = None
    if sys.platform != 'win32':
        settings = termios.tcgetattr(sys.stdin)

    rclpy.init()
    node = Node('rov_teleop_key')
    pub = node.create_publisher(Twist, '/cmd_vel', 10)

    print(INSTRUCTIONS)

    speed_surge = 0.5
    speed_heave = 0.4
    speed_yaw = 0.8

    try:
        while rclpy.ok():
            key = get_key(settings)
            twist = Twist()

            if key.lower() == 'w':
                twist.linear.z = speed_heave
                print(">> NAIK (Ascend)")
            elif key.lower() == 's':
                twist.linear.z = -speed_heave
                print(">> MENYELAM (Descend) -> Menuju lapisan anoksia Waduk Saguling")
            elif key.lower() == 'i':
                twist.linear.x = speed_surge
            elif key.lower() == 'k':
                twist.linear.x = -speed_surge
            elif key.lower() == 'j':
                twist.angular.z = speed_yaw
            elif key.lower() == 'l':
                twist.angular.z = -speed_yaw
            elif key.lower() == 'u':
                twist.linear.y = -speed_surge
            elif key.lower() == 'o':
                twist.linear.y = speed_surge
            elif key == ' ':
                twist = Twist()
                print(">> STOP")
            elif key == '\x03':  # CTRL+C
                break

            if key:
                pub.publish(twist)

            rclpy.spin_once(node, timeout_sec=0.05)

    except Exception as e:
        print(f"Teleop error: {e}")
    finally:
        twist = Twist()
        pub.publish(twist)
        if sys.platform != 'win32' and settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, settings)
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
