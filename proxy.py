#!/usr/bin/env python
#coding:utf-8
import socket
import sys
import re
import os
import time
import select
import threading
import yaml

HEADER_SIZE = 4096

mode = None
host = None  # '127.0.0.1'
port = None  # 9292
remote_ip = None
remote_port = None

#子进程进行socket 网络请求
def http_socket(client, addr):
    #创建 select 检测 fd 列表
    inputs  = [client] # 读信息socket列表
    outputs = []
    remote_socket = None
    remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    if mode == 'client':
        remote_socket.connect((remote_ip, remote_port))
        inputs.append(remote_socket)
    # print("client connent:{0}:{1}".format(addr[0], addr[1]))
    while True:
        readable, writable, exceptional = select.select(inputs, outputs, inputs)
        try:
            for read_socket in readable:
                if read_socket is client:
                    #读取 http 请求头信息
                    data = read_socket.recv(HEADER_SIZE)
                    # print(str(data))
                    data = data[::-1]  # simple encryption or dencryption
                    if remote_socket is None:  # Proxy Client端不会进入这一分支
                        #拆分头信息
                        host_url = data.split(b"\r\n")[0].split(b" ")
                        method, host_addr, protocol = map(
                            lambda x: x.decode('utf-8').strip(),
                            host_url
                        )
                        #如果 CONNECT 代理方式
                        if method == "CONNECT":
                            host, port = host_addr.split(":")
                        else:
                            host_addr = data.split(b"\r\n")[1].decode('utf-8').split(":")
                            #如果未指定端口则为默认 80
                            if 2 == len(host_addr):
                                host_addr.append("80")
                            name, host, port = map(lambda x: x.strip(), host_addr)
                        #建立 socket tcp 连接
                        remote_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        remote_socket.connect((host, int(port)))
                        inputs.append(remote_socket)
                        if method == "CONNECT":
                            start_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(time.time()))
                            msg = "HTTP/1.1 200 Connection Established\r\nFiddlerGateway: Direct\r\nStartTime: {0}\r\nConnection: close\r\n\r\n".format(start_time)
                            read_socket.sendall(bytes(msg, encoding='utf-8'))
                            continue
                    #发送原始请求头
                    remote_socket.sendall(data)
                else:
                    #接收数据并发送给浏览器
                    response = read_socket.recv(HEADER_SIZE)
                    if response:
                        client.sendall(response)
        except Exception as e:
            # pass
            print("http socket error {0}".format(e.with_traceback()))
            exit()


if __name__ == '__main__':
    with open('config.yaml') as f:
        cfg = yaml.load(f)
    # global mode
    # global host
    # global port
    mode = cfg['MODE']
    host = cfg['HOST']
    port = cfg['PORT']
    
    if mode not in ['client', 'server']:
        raise Exception('MODE should be client or server.')
    if mode == 'client':
        remote_ip = cfg['REMOTE']
        remote_port = cfg['RPORT']
    #创建socket对象
    http_server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        http_server.bind((host, port))
    except Exception as e:
        sys.exit("python proxy bind error {0}".format(e))

    print("python proxy start")

    http_server.listen(200)

    while True:
        client, addr = http_server.accept()
        print(addr)
        http_thread = threading.Thread(target=http_socket, args=(client, addr))
        http_thread.start()
        time.sleep(1)

    #关闭所有连接
    http_server.close()
    print("python proxy close")