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
HEX_FILTER = ''.join([(len(repr(chr(i))) == 3) and chr(i) or '.' for i in range(256)])

# hexdump函数能接收bytes或string类型的输入，并将其转换为十六进制格式输出到屏幕上
# 它能同时以十六进制数和ASCII可打印字符的格式，输出数据包的详细内容。
# 这有助于理解未知协议的格式，或是在明文协议里查找用户的身份凭证等
def hexdump(src, length=16, show=True):
    if isinstance(src, bytes):      # 判断src是否为bytes类型
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
        hexa = ' '.join([f'{ord(c):02X}' for c in word])
        # 将word变量起始点的偏移、其十六进制表示和可打印字符表示形式打包成一行字符串，放入results数组
        hexwidth = length * 3
        # 以f开头，包含的{}表达式在程序运行时会被表达式的值代替
        results.append(f'{i:04x} {hexa:<{hexwidth}} {printable}')
        print()
    if show:
        for line in results:
            print(line)
    else:
        return results

# 从代理两端接收数据
def receive_from(connection):
    buffer = b""    # 用来存储socket对象返回的数据
    connection.settimeout(5)    # 设定超时时间为5秒
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

