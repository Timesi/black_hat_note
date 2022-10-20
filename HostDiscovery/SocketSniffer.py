# 基于UDP的主机发现工具
import socket
import os

# 监听主机
HOST = "127.0.0.1"


def main():
    # 创建原始套接字,绑定在公开接口上
    # 判断是否为Windows，如果是则允许嗅探任何协议的所有流入数据
    # 如果不是Windows，指定ICMP协议来嗅探
    if os.name == "nt":
        socket_protocol = socket.IPPROTO_IP
    else:
        socket_protocol = socket.IPPROTO_ICMP

    # 构建一个socket对象，传入嗅探网卡数据所需的参数
    sniffer =socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_protocol)
    sniffer.bind((HOST, 0))

    # 设置在捕获的数据包中的包含IP头
    # setsockopt函数用于对socket函数补充
    # socket.IPPROTO_IP选项是指定控制套接字的层次为IP选项
    sniffer.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

    # 判断是否在Windows上，如果是则额外发送一条IOCTL消息启用网卡的混杂模式
    if os.name == 'nt':
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_ON)

    # 只输出了原始数据包的全部内容
    print(sniffer.recvfrom(65565))

    # 嗅探完一个数据包后，再次检测现在是不是在Windows平台，关闭网卡的混杂模式
    if os.name == 'nt':
        sniffer.ioctl(socket.SIO_RCVALL, socket.RCVALL_OFF)

if __name__ == '__main__':
    main()



