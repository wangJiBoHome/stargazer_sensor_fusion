#! /usr/bin/env python3
import rospy
import math
from nav_msgs.msg import Odometry
from tf.transformations import euler_from_quaternion, quaternion_from_euler
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from itertools import groupby

w_robot = 1.2                   # width of robot
gamma = 5
angle_range = 360
angle = 0

"""

LiDAR로부터 관측된 특정 time step에서의 data 값은 (dis, angle) 형태로 저장이 되어야 하는 것이 기본이다.

"""

# theta_goal을 받아줄 수 있어야 함으로 또 지정을 해줄 수 있는 코드를 짜야함
theta_goal = 0


# callback 함수
def rplidar_callback(msg):

    for i in range(msg.ranges):
        print("{} m at {} index".format(msg.ranges[i], i))

    min_dis = 1e10

    for i in msg.ranges:
        if (i != 0) and (i < min_dis):
            min_dis = i 
        

    #print("minimum distace:", min_dis)

    sensor_data = []            # 전처리될 lidar data들                                  
    threshold_distance = 5                                                             
    threshold_continuity = 3    # number of continous elements                                                          
    filtered_sensor_data = []

    for angle, dis in enumerate(msg.ranges):
        #print("angle: {}, dis: {}".format(angle, dis))
        if 0 < dis <= threshold_distance:
            sensor_data.append( (angle, dis) )
        else:
            sensor_data.append( (0, 0) )

        #print("sensor_data: ", sensor_data)
                                                                                   
    while True:                                                                        
        obs = []                                                                       
        for data in sensor_data:                       # (angle, dis) 형태의 tuple                                                                                       
            if data[1] > 0:                                                 
                obs.append(data)                                                          
                sensor_data = sensor_data[1:]                                                                                   
            else:                                                                                                                     
                sensor_data = sensor_data[1:]                                                          
                break                                                                  
                                                                                    
        if (len(obs) != 0) and (len(obs) > threshold_continuity) :                     
            filtered_sensor_data.append(obs)                                           
                                                                                    
        if len(sensor_data) == 0:                                                              
            break                                                                      

                                                                        
    #print("recognized obstacle:", filtered_sensor_data) 

    #fancy print summary
    #print("[OBSTACLE INFO]")
    #for k, obs in enumerate(filtered_sensor_data):
    #    print("Obstacle No: {}".format(k+1))
    #    print("Obstacle Range: {} - {} degrees".format(obs[0][0], obs[-1][0]))
    #    print("-------------------------------")    
    #print()                           

    d_max = 20                                              # Hokuyo LiDAR의 최대 감지 거리 (20m라고 현재 가정)

    # POTENTIAL FIELD 구축

    
    total_field = 0
    total_field_list = []
    attractive_field = 0
    heading_angle = 0

    for theta_i in range(angle_range):                      # 0 ~ 360 degrees

        repulsive_field = 0

        for obs in filtered_sensor_data:                    # for each obstacle in filtered_sensor_data, (for every kth obstacles, )
            _sum = 0
            for i in obs:
                _sum += i[1]
                                                                                                                                
            theta_k = obs[int(len(obs) / 2)][0]             # center angle of each obstacle

            d_k = _sum / len(obs)                           # average distance for each obstacles          
            pi_k = len(obs) / 180 * math.pi                 # occupying angle for each obstacles

            sigma_k = math.atan2(d_k * math.tan(pi_k/2) + w_robot / 2, d_k)             # w_robot / 2를 해줘서 장애물의 크기를 조금씩 키움 (2보다 작아도 됨)
            #print(sigma_k)
            PI_k = 2 * sigma_k              # each obstacle's occupying range given from average distance and angle

            # repulsive field (Gaussian likelihood function)
            _d_k = d_max - d_k * d_max
            A_k = _d_k * math.exp(0.5)

            repulsive_field += A_k * math.exp( -((theta_k-theta_i) / 180 * math.pi)**2 / (2 * pow(sigma_k, 2) ) ) # 이 부분하고 위에 sigma_k 구하는 부분 이상
        
        attractive_field = gamma * abs( (theta_goal - theta_i) / 180 * math.pi )

        total_field = attractive_field + repulsive_field

        #print(attractive_field, repulsive_field)

        total_field_list.append( (total_field, theta_i) )

    #print(total_field_list)

    
    #print(total_field_list)
    min_total_field = [total_field_list[0]]
    
    #print(total_field_list)

    for pf, angle in total_field_list:    
        
        if pf < min_total_field[0][0]:
            min_total_field.pop()
            min_total_field.append((pf, angle))

    heading_angle = min_total_field[0][1] / 180 * math.pi 
    angle = heading_angle       
    #print(heading_angle)

roll = pitch = yaw = 0.0
target = 90
kp = 0.5
 
def get_rotation (msg):
    global roll, pitch, yaw
    orientation_q = msg.pose.pose.orientation
    orientation_list = [orientation_q.x, orientation_q.y, orientation_q.z, orientation_q.w]
    (roll, pitch, yaw) = euler_from_quaternion (orientation_list)
    #print(yaw)



rospy.init_node("ODG-PF")
sub = rospy.Subscriber('/scan', LaserScan, rplidar_callback)
sub = rospy.Subscriber ('/odom', Odometry, get_rotation)
pub = rospy.Publisher('cmd_vel', Twist, queue_size=1)
r = rospy.Rate(10)
command =Twist()


while not rospy.is_shutdown():
    #quat = quaternion_from_euler (roll, pitch,yaw)
    #print quat
    target_rad = target*math.pi/180
    command.angular.z = kp * (target_rad-yaw)
    pub.publish(command)
    #print("target={} current:{}", target,yaw)
    r.sleep()

#rotate(angle)
#rospy.spin()
