# Simple_TCP_Proxy
# hexdump函数：把本地设备和远程设备之间的通信过程显示到屏幕上；
# receive_from函数：从本地设备或远程设备的入口socket接收数据；
# proxy_handler函数：控制远程设备和本地设备之间的流量方向；
# server_loop函数：创建一个监听socket，并把它传给我们的proxy_handler
import sys
import socket
import threading
from unittest import result

# 在所有可打印字符（长度为3）的位置上，保持原有的字符不变；在所有不可打印字符的位置上，放一个句点“.”
HEX_FILTER = "".join([(len(repr(chr(i))) == 3) and chr(i) or "." for i in range(256)])

# hexdump函数能接收bytes或string类型的输入，并将其转换为十六进制格式输出到屏幕上
# 它能同时以十六进制数和ASCII可打印字符的格式，输出数据包的详细内容。
# 这有助于理解未知协议的格式，或是在明文协议里查找用户的身份凭证等
def hexdump(src, length=16, show=True):
    if isinstance(src, bytes):  # 判断src是否为bytes类型
        # 如果传进来的参数是bytes类型的话，就调用decode函数将它转换为string类型
        src = src.decode()

    results = list()
    for i in range(0, len(src), length):
        # 取一小段数据放到word中
        word = str(src[i : i + length])
        # 调用内置的translate函数把整段数据转换成可打印字符的格式，保存到printable变量里
        # 将HEX_FILTER为翻译表
        printable = word.translate(HEX_FILTER)
        # 将word中的数据转换为十六进制保存在变量hexa中
        hexa = " ".join([f"{ord(c):02X}" for c in word])
        # 将word变量起始点的偏移、其十六进制表示和可打印字符表示形式打包成一行字符串，放入results数组
        hexwidth = length * 3
        # 以f开头，包含的{}表达式在程序运行时会被表达式的值代替
        results.append(f"{i:04x} {hexa:<{hexwidth}} {printable}")
        print()
    if show:
        for line in results:
            print(line)
    else:
        return results


# 从代理两端接收数据
def receive_from(connection):
    buffer = b""  # 用来存储socket对象返回的数据
    connection.settimeout(5)  # 设定超时时间为5秒
    try:
        # 创建一个循环，不断把返回的数据写进buffer，直到数据读完或者连接超时为止。
        # 最后，把buffer返回给调用方，这个调用方可能是本地设备，也可能是远程设备。
        while True:
            data = connection.recv(4096)
            if not data:
                break
            buffer += data
    except Exception as e:
        pass
    return buffer


# 在代理转发数据包之前，修改一下回复的数据包或请求的数据包
def request_handler(buffer):
    # perform packet modifications
    return buffer


def response_handler(buffer):
    # perform packet modifications
    return buffer


def proxy_handler(client_socket, remote_host, remote_port, receive_first):
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 连接远程主机
    remote_socket.connect((remote_host, remote_port))

    # 进入主循环之前，先确认是否需要先从服务器那边接收一段数据
    if receive_first:
        # 对通信两端分别调用receive_from函数，从已连接的socket对象中收取数据
        remote_buffer = receive_from(remote_socket)
        hexdump(remote_buffer)

    # 把数据交给response_handler函数,等它处理数据后再转发给本地客户端
    remote_buffer = response_handler(remote_buffer)

    if len(remote_buffer):
        print("[<==] sending %d bytes to localhost." % len(remote_buffer))
        client_socket.send(remote_buffer)

    # 开启一个循环，不断地从本地客户端读取数据，处理数据，转发给远程服务器，
    # 从远程服务器读取数据，处理数据，转发给本地客户端，直到再也读不到任何数据为止。
    # 当通信两端都没有任何数据时关闭两端的socket，退出代理循环
    while True:
        # 处理本地客户端的数据
        local_buffer = receive_from(client_socket)
        if len(local_buffer):
            line = "[==>]Received %d bytes from localhost." % len(local_buffer)
            print(line)
            hexdump(local_buffer)

            local_buffer = request_handler(local_buffer)
            remote_socket.send(local_buffer)
            print("[==>] Sent to remote.")

        # 处理远端服务器数据
        remote_buffer = receive_from(remote_socket)
        if len(remote_buffer):
            print("[<==]Received %d bytes from remote." % len(remote_socket))
            hexdump(local_buffer)

            remote_buffer = request_handler(remote_buffer)
            remote_socket.send(remote_buffer)
            print("[<==] Sent to localhost.")

        if not len(local_buffer) or not len(remote_buffer):
            client_socket.close()
            remote_socket.close()
            print("[*]No more data. closing connections.")
            break


# 创建和管理连接
def server_loop(local_host, local_port, remote_host, remote_port, receive_first):
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # 创建一个socket并绑定到本地端口开始监听
    try:
        server.bind((local_host, local_port))
    except Exception as e:
        print(" problem on bind: %r" % e)

        print("[!!] Failed to listen on %s:%d" % (local_host, local_port))
        print("[!!] check for other listening sockets or correct permissions. ")
        sys.exit(e)

    print("[*] Listening on %s: %d" % (local_host, local_port))
    server.listen(5)

    # 每出现一个新连接就新开一个线程，将新连接交给proxy_handler函数
    while True:
        client_socket, addr = server.accept()
        line = "> Received incoming connection from %s:%d" % (addr[0], addr[1])
        print(line)
        proxy_thread = threading.Thread(
            target=proxy_handler,
            args=(client_socket, remote_host, remote_port, receive_first),
        )
        proxy_thread.start()


def main():
    if len(sys.argv[1:] != 5):
        print("Usage: ./proxy.py [ localhost] [localport]", end="")
        print("[remotehost] [ remoteport] [ receive_first]")
        print("Example: ./proxy.py 127.0.0.1 9000 10.12.132.1 9000 True")
        sys.exit(0)

    local_host = sys.argv[1]
    local_port = int(sys.argv[2])

    remote_host = sys.argv[3]
    remote_port = int(sys.argv[4])

    receive_first = sys.argv[5]

    if "True" in receive_first:
        receive_first = True
    else:
        receive_first = False

    server_loop(local_host, local_port, remote_host, remote_port, receive_first)


if __name__ == "__main___":
    main()
