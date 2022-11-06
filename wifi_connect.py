# MJPEG Streaming AP.
#
# 这个例子展示了如何在AccessPoint模式下进行MJPEG流式传输。
# Android上的Chrome，Firefox和MJpegViewer App已经过测试。
# 连接到OPENMV_AP并使用此URL：http://192.168.1.1:8080查看流。

import sensor, image, time, network, usocket, sys, pyb, math
from pyb import Pin, Timer, LED, UART
led = pyb.LED(1)

SSID ='OPENMV_AP'    # Network SSID
KEY  ='1234567890'   # wifi密码(必须为10字符)
HOST = ''           # 使用第一个可用的端口
PORT = 8080         # 任意非特权端口

#黑色点阈值
red_threshold = [(44, 72, 23, 38, -5, 19)]
#xy平面误差数据
err_x = 0
err_y = 0
#发送数据
uart_buf = bytearray([0xA5,0x5A,0x00,0x00,0x00])

#串口三配置
uart = UART(3, 115200)
uart.init(115200, bits=8, parity=None, stop=1)

# 重置传感器
sensor.reset()
# 设置传感器设置
sensor.set_contrast(1)
sensor.set_brightness(1)
sensor.set_saturation(1)
sensor.set_gainceiling(16)
sensor.set_framesize(sensor.QQVGA)
sensor.set_pixformat(sensor.RGB565)

sensor.skip_frames(20)#相机自检几张图片
sensor.set_auto_whitebal(False)#关闭白平衡
clock = time.clock()#打开时钟

# 在AP模式下启动wlan模块。
wlan = network.WINC(mode=network.WINC.MODE_AP)
wlan.start_ap(SSID, key=KEY, security=wlan.WEP, channel=2)

#您可以阻止等待客户端连接
#print(wlan.wait_for_sta(10000))

def start_streaming(s):
    print ('Waiting for connections..')
    client, addr = s.accept()
    # 将客户端套接字超时设置为2秒
    client.settimeout(2.0)
    print ('Connected to ' + addr[0] + ':' + str(addr[1]))

    # 从客户端读取请求
    data = client.recv(1024)
    # 应该在这里解析客户端请求

    # 发送多部分head
    client.send("HTTP/1.1 200 OK\r\n" \
                "Server: OpenMV\r\n" \
                "Content-Type: multipart/x-mixed-replace;boundary=openmv\r\n" \
                "Cache-Control: no-cache\r\n" \
                "Pragma: no-cache\r\n\r\n")

    # FPS clock
    clock = time.clock()

    # 开始流媒体图像
    #注：禁用IDE预览以增加流式FPS。
    while (True):
        clock.tick() # 跟踪snapshots()之间经过的毫秒数。
        frame = sensor.snapshot()
        cframe = frame.compressed(quality=35)
        header = "\r\n--openmv\r\n" \
                 "Content-Type: image/jpeg\r\n"\
                 "Content-Length:"+str(cframe.size())+"\r\n\r\n"
        client.send(header)
        client.send(cframe)
        clock.tick()
        img = sensor.snapshot()
        #寻找blob
        blobs = img.find_blobs(red_threshold)
        if blobs:
            led.on()
            most_pixels = 0
            largest_blob = 0
            for i in range(len(blobs)):
                #目标区域找到的颜色块可能不止一**重点内容**个，找到最大的一个
                if blobs[i].pixels() > most_pixels:
                    most_pixels = blobs[i].pixels()
                    largest_blob = i
                    #位置环用到的变量
                    err_x = int(60 - blobs[largest_blob].cy())
                    err_y = int(blobs[largest_blob].cx() - 80)
            img.draw_cross(blobs[largest_blob].cx(),blobs[largest_blob].cy())#调试使用
            img.draw_rectangle(blobs[largest_blob].rect())
        else:
            led.off()
            err_x = 0
            err_y = 0
        #数组中数据写入
        uart_buf = bytearray([0x55,err_x,err_y,err_x + err_y])
        print(err_x,err_y)
        uart.write(uart_buf)
        print(clock.fps())

while (True):
    # 创建服务器套接字
    s = usocket.socket(usocket.AF_INET, usocket.SOCK_STREAM)
    # Bind and listen
    s.bind([HOST, PORT])
    s.listen(5)

    # 设置服务器套接字超时
    # 注意：由于WINC FW bug，如果客户端断开连接，服务器套接字必须
    # 关闭并重新打开。在这里使用超时关闭并重新创建套接字。
    s.settimeout(100)
    start_streaming(s)
