import argparse
import socket
import shlex
import subprocess
import sys
import textwrap
import threading


def execute(cmd):
    # execute函数将会接受一条命令并执行，然后将结果作为一段字符串返回
    cmd = cmd.strip()
    if not cmd:
        return
    # subprocess库提供了一组强大的进程创建接口，让你可以通过多种方式调用其他程序。
    # check_output函数会在本机运行一条命令，并返回该命令的输出
    output = subprocess.check_output(shlex.split(cmd), stderr=subprocess.STDOUT)
    return output.decode()


class NetCat:
    # 我们用main代码块传进来的命令行参数和缓冲区数据，初始化一个NetCat对象，然后创建一个socket对象
    def __init__(self, args, buffer=None):
        self.args = args
        self.buffer = buffer
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    # run函数是NetCat对象的执行入口
    # 如果NetCat对象是接收方，run就执行listen函数
    # 如果是发送方，run就执行send函数
    def run(self):
        if self.args.listen:
            self.listen()
        else:
            self.send()

    # 发送数据
    def send(self):
        # 连接到target:port
        self.socket.connect((self.args.target, self.args.port))
        # 如果缓冲区中有数据的话，就先将数据发送过去
        if self.buffer:
            self.socket.send(self.buffer)
        # 创建个try/catch块，这样就能直接用Ctrl+C组合键手动关闭连接
        try:
            # 创建一个大循环，一轮一轮地接收target返回的数据
            while True:
                recv_len = 1
                response = ""
                # 读取socket本轮返回的数据,如果socket里的数据目前已经读到头，就退出小循环
                while recv_len:
                    data = self.socket.recv(4096)
                    recv_len = len(data)
                    response += data.decode()  # data.decode 表示把二进制解码成为字符串
                    if recv_len < 4096:
                        break
                # 检查刚才有没有实际读出什么东西来，如果读出了什么，就输出到屏幕上，并暂停，
                # 等待用户输入新的内容，再把新的内容发给target
                if response:
                    print(response)
                    buffer = input(">")
                    buffer += "\n"
                    self.socket.send(buffer.encode())  # str.encode 表示把字符串编码成为二进制
        except KeyboardInterrupt:
            print("User terminated.")
            self.socket.close()
            sys.exit()

    # 监听数据
    def listen(self):
        self.socket.bind((self.args.target, self.args.port))
        # listen(n)传入的值, n表示的是服务器拒绝(超过限制数量的)连接之前，操作系统可以挂起的最大连接数量。n也可以看作是"排队的数量"
        self.socket.listen(5)

        # 用一个循环监听新连接,并把已连接的socket对象传递给handle函数
        while True:
            (
                client_socket,
                _,
            ) = self.socket.accept()  # accept()等待传入连接。,返回代表连接的新套接字以及客户端的地址。

            # 给每个客户端创建一个独立的线程进行管理
            client_thread = threading.Thread(target=self.handle, args=(client_socket,))
            client_thread.start()

    # 执行传入的任务
    def handle(self, client_socket):
        # 如果要执行命令，handle函数就会把该命令传递给execute函数
        # 然后把输出结果通过socket发回去
        if self.args.execute:
            output = execute(self.args.execute)
            client_socket.send(output.encode())
        elif self.args.upload:
            file_buffer = b""
            while True:
                # recv并不是取完对方发送的数据，而是取一次,取多少字节，取决于recv的参数buffsize
                data = client_socket.recv(4096)
                if data:
                    file_buffer += data
                else:
                    break
        elif self.args.command:
            # 创建shell，先创建一个循环，向发送方发一个提示符，
            # 然后等待其发回命令。每收到一条命令，就用execute函数执行它，然后把结果发回发送方
            cmd_buffer = b""
            while True:
                try:
                    client_socket.send(b"BHP:#>")
                    while "\n" not in cmd_buffer.decode():
                        cmd_buffer += client_socket.recv(64)
                    response = execute(cmd_buffer.decode())
                    if response:
                        client_socket.send(response.encode())
                    cmd_buffer = b""
                except Exception as e:
                    print(f"server killed {e}")
                    self.socket.close()
                    sys.exit()


if __name__ == "__main__":
    # 使用argparse库是python标准库里面用来处理命令行参数的库
    # 传递不同的参数，就能控制这个程序执行不同的操作
    parser = argparse.ArgumentParser(  # 创建一个解析对象
        description="BHP Net Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        # 帮助信息,程序启动的时候如果使用--help参数，就会显示这段信息
        epilog=textwrap.dedent(
            """
                netcat.py -t 192.168.1.108 -p 5555 -l -c # command shell
                netcat.py -t 192.168.1.108 -p 5555 -l -u=mytest.txt # upload to file
                netcat.py -t 192.168.1.108-p 5555 -l -e=\ "cat /etc/passwd \ " # execute command
                echo 'ABC' / ./netcat.py -t 192.168.1.108 -p 135 # echo text to server port 135
                netcat.py -t 192.168.1.108 -p 5555 # connect to server
            """
        ),
    )
    # 通过add_argument()方法来给ArgumentParser对象添加新的命令行参数
    # 参数的类型和相应的处理方法由不同的参数决定
    # action='store_true'，只要运行时该变量有传参就将该变量设为True

    # 因为发送方和接收方都会运行这个程序，所以传进来的参数会决定这个程序接下来是要发送数据还是要进行监听
    # 使用了-c、-e和-u这三个参数，就意味着要使用-l参数，因为这些行为都只能由接收方来完成
    # 而发送方只需要向接收方发起连接，所以它只需要用-t和-p两个参数来指定接收方。

    # -c参数,打开一个交互式的命令行shell；
    parser.add_argument("-c", "--command", action="store_true", help="command shell")
    # -e参数,执行一条命令
    parser.add_argument("-e", "--execute", help="execute specified command")
    # -l参数,创建一个监听器
    parser.add_argument("-l", "--listen", action="store_true", help="listen ")
    # -p参数,指定要通信的端口
    parser.add_argument("-p", "--port", type=int, default=5555, help="specified port ")
    # -t参数,指定要通信的目标IP地址
    parser.add_argument("-t", "--target", default="192.168.1.203", help="specified IP")
    # -u参数,指定要上传的文件
    parser.add_argument("-u", "--upload", help="upload file")

    # 如果确定了程序要进行监听，我们就在缓冲区里填上空白数据，把空白缓冲区传给NetCat对象.
    # 反之，我们就把stdin里的数据通过缓冲区传进去。最后调用NetCat类的run函数来启动它
    # 使用 parse_args() 解析添加的参数
    args = parser.parse_args()
    if args.listen:
        buffer = ""
    else:
        buffer = sys.stdin.read()

    nc = NetCat(args, buffer.encode())
    nc.run()
