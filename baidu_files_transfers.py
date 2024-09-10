#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
import argparse
import yaml
import time
import re
import random
import requests
import urllib3
import urllib
import traceback


# 公共请求头
request_header = {
    'Host': 'pan.baidu.com',
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
     'User_Agent' : 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Sec-Fetch-Dest': 'document',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
    'Sec-Fetch-Site': 'same-site',
    'Sec-Fetch-Mode': 'navigate',
    'Referer': 'https://pan.baidu.com',
    'Accept-Encoding': 'gzip, deflate, br',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-US;q=0.7,en-GB;q=0.6,ru;q=0.5',
}
session = requests.session()
urllib3.disable_warnings()
s = requests.session()
s.trust_env = False


def get_bdstoken():
    # 获取bdstoken函数
    url = 'https://pan.baidu.com/api/gettemplatevariable?clienttype=0&app_id=250528&web=1&fields=[%22bdstoken%22,%22token%22,%22uk%22,%22isdocuser%22,%22servertime%22]'
    response = s.get(url=url, headers=request_header, timeout=20, allow_redirects=True, verify=False)
    return response.json()['errno'] if response.json()['errno'] != 0 else response.json()['result']['bdstoken']


def get_dir_list(bdstoken, dir='/'):
    # 获取云盘目录列表函数
    name_list = []
    page = 1
    num = 1000
    while True:
        url = f'https://pan.baidu.com/api/list?order=time&desc=1&showempty=0&web=1&page={page}&num={num}&dir={urllib.parse.quote(dir)}&bdstoken={bdstoken}'
        response = s.get(url=url, headers=request_header, timeout=15, allow_redirects=False, verify=False)
        res_json = response.json()
        if res_json['errno'] == 0 and res_json['list']:
            name_list += res_json['list']
        else:
            break
        page += 1
    return name_list


def get_share_dir_list(user_id, share_id, share_dir_name):
    # 获取分享链接目录列表函数
    fs_id_list = []
    num  = 100
    print("开始获取父目录")
    page = 1
    while True:
        url = f"https://pan.baidu.com/share/list?uk={user_id}&shareid={share_id}&order=other&desc=1&showempty=0&web=1&page={page}&num={num}&dir={urllib.parse.quote(share_dir_name)}"
        print(url)
        response = s.get(url=url, headers=request_header, verify=False)
        res_json = response.json()
        if res_json['errno'] == 0 and res_json['list']:
            fs_id_list += res_json['list']
        else:
            break
        page += 1
    return fs_id_list


def check_links(link_url, pass_code, bdstoken):
    # 验证链接函数
    # 验证提取码
    if pass_code:
        # 生成时间戳
        t_str = str(int(round(time.time() * 1000)))
        check_url = 'https://pan.baidu.com/share/verify?surl=' + link_url[25:48] + '&bdstoken=' + bdstoken + '&t=' + t_str + '&channel=chunlei&web=1&clienttype=0'
        post_data = {'pwd': pass_code, 'vcode': '', 'vcode_str': '', }
        response_post = s.post(url=check_url, headers=request_header, data=post_data, timeout=10, allow_redirects=False, verify=False)
        # 在cookie中加入bdclnd参数
        if response_post.json()['errno'] == 0:
            bdclnd = response_post.json()['randsk']
        else:
            return response_post.json()['errno']
        if bool(re.search('BDCLND=', request_header['Cookie'], re.IGNORECASE)):
            request_header['Cookie'] = re.sub(r'BDCLND=(\S+);?', r'BDCLND=' + bdclnd + ';', request_header['Cookie'])
        else:
            request_header['Cookie'] += ';BDCLND=' + bdclnd
    # 获取文件信息
    response = s.get(url=link_url, headers=request_header, timeout=15, allow_redirects=True, verify=False).content.decode("utf-8")
    shareid_list = re.findall('"shareid":(\\d+?),"', response)
    user_id_list = re.findall('"share_uk":"(\\d+?)","', response)
    fs_id_list = re.findall('"fs_id":(\\d+?),"', response)
    info_title_list = re.findall('<title>(.+)</title>', response)
    server_filedir = re.findall('"server_filename":"(.*?)",',response)
    print("--------++++++++++++++++++","link_url: ",link_url, "shareid_list: ",shareid_list,"user_id_list: ",user_id_list,"fs_id_list: ", fs_id_list,"info_title_list: ",info_title_list, "server_filename: ",server_filedir)
    if not shareid_list:
        return 1
    elif not user_id_list:
        return 2
    elif not fs_id_list:
        return info_title_list[0] if info_title_list else 3
    else:
        return [shareid_list[0], user_id_list[0], fs_id_list, server_filedir[0]]


def create_dir(dir_name, bdstoken):
    # 新建目录函数
    url = 'https://pan.baidu.com/api/create?a=commit&bdstoken=' + bdstoken
    post_data = {'path': dir_name, 'isdir': '1', 'block_list': '[]', }
    response = s.post(url=url, headers=request_header, data=post_data, timeout=15, allow_redirects=False, verify=False)
    print(post_data)
    return response.json()['errno']


def transfer_files(user_id, share_id, fs_id_list, dir_name, bdstoken):
    # 转存文件函数
    url = f'https://pan.baidu.com/share/transfer?shareid={share_id}&from={user_id}&bdstoken={bdstoken}&channel=chunlei&web=1&clienttype=0'

    fs_id = ','.join(i for i in fs_id_list)
    post_data = {'fsidlist': '[' + fs_id + ']', 'path': dir_name, }
    print(post_data, url)
    response = s.post(url=url, headers=request_header, data=post_data, timeout=15, allow_redirects=False, verify=False)
    print(response.text)
    return response.json()['errno']


def check_link_type(link_list_line):
    # 检测链接种类
    if link_list_line.find('https://pan.baidu.com/s/') >= 0:
        link_type = '/s/'
    return link_type


def recursive_transfer_files(user_id, share_id, fs_id_list, share_dir_name, local_dir_name, bdstoken):
    # 递归转存文件函数
    # 执行转存文件
    transfer_files_reason = transfer_files(user_id, share_id, fs_id_list, os.path.dirname(local_dir_name+share_dir_name), bdstoken)
    if transfer_files_reason == 0:
        print(f'转存成功\n')
    elif transfer_files_reason == -4:
        print(f'转存失败,无效登录.请退出账号在其他地方的登录\n')
    elif transfer_files_reason == 4 or transfer_files_reason == -8:
        print(f'转存失败,目录中已有同名文件或文件夹存在\n')
    elif transfer_files_reason == 12:
        print(f'转存失败,转存文件数超过限制\n, 开始分批转存......')
        new_fs_id_list = get_share_dir_list(user_id, share_id, share_dir_name)
        create_dir(''.join([local_dir_name, share_dir_name]), bdstoken)
        if new_fs_id_list:
            for curr_fs_id_list in new_fs_id_list:
                time.sleep(round(random.uniform(0.001, 5.01), 3))
                print(fs_id_list,"sleeptime: ",round(random.uniform(0.001, 5.01), 3))
                recursive_transfer_files(user_id, share_id, [str(curr_fs_id_list['fs_id'])], curr_fs_id_list['path'], local_dir_name, bdstoken)


def main():
    # 主程序
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--url", help="url")
    parser.add_argument("-f", "--config", default="config.yaml", help="config yaml file path")
    parser.add_argument("-c", "--cookie", help="cookie of pan.baidu.com")
    parser.add_argument("-p", "--password", help="share password")
    parser.add_argument("-d", "--dir", help="dir name")

    args = parser.parse_args()
    dir_name = args.dir
    cookie = args.cookie
    link_url = args.url

    if os.path.isfile(args.config):
        with open(args.config) as fp:
            config = yaml.safe_load(fp.read())
            if "cookie" in config:
                cookie = config["cookie"]
    # 获取和初始化数据
    request_header['Cookie'] = cookie
    # 开始运行函数
    # 开始运行函数
    try:
        # 检查cookie输入是否正确
        if any([ord(word) not in range(256) for word in cookie]) or cookie.find('BAIDUID=') == -1:
            print('百度网盘cookie输入不正确,请检查cookie后重试.' + '\n')
            sys.exit()

        # 执行获取bdstoken
        bdstoken = get_bdstoken()
        print(bdstoken,"bdstoken-------------------------------------")
        if isinstance(bdstoken, int):
            print('没获取到bdstoken,错误代码:' + str(bdstoken) + '\n')
            sys.exit()

        # 执行获取本人网盘目录列表
        dir_list_json = get_dir_list(bdstoken)
        if type(dir_list_json) != list:
            print('没获取到网盘目录列表,请检查cookie和网络后重试.' + '\n')
            sys.exit()
        # 执行新建目录
        dir_list = [dir_json['server_filename'] for dir_json in dir_list_json]
        if dir_name and dir_name not in dir_list:
            create_dir_reason = create_dir(dir_name, bdstoken)
            if create_dir_reason != 0:
                print('文件夹名带非法字符,请改正文件夹名称后重试.' + '\n')
                sys.exit()

        # 执行转存
        # 处理http链接
        link_url = link_url.replace("http://", "https://")
        # 处理(https://pan.baidu.com/s/1tU58ChMSPmx4e3-kDx1mLg?pwd=123w)格式链接
        link_url = link_url.replace("?pwd=", " ")
        # 处理旧格式链接
        link_url = link_url.replace("https://pan.baidu.com/share/init?surl=", "https://pan.baidu.com/s/1")
        # 判断连接类型
        link_type = check_link_type(link_url)
        # 链接有效性
        check_links_reason = ""
        # 处理(https://pan.baidu.com/s/1tU58ChMSPmx4e3-kDx1mLg 123w)格式链接
        if link_type == '/s/':
            link_url_org, pass_code_org = re.sub(r'提取码*[：:](.*)', r'\1', link_url.lstrip()).split(' ', maxsplit=1)
            [link_url, pass_code] = [link_url_org.strip()[:47], pass_code_org.strip()[:4]]
            shareid_list,user_id_list,fs_id_list,server_filedir = check_links(link_url, pass_code, bdstoken)
            recursive_transfer_files(user_id_list, shareid_list, fs_id_list, '/'+server_filedir, '/' + dir_name, bdstoken)
        else:
            print('访问链接返回错误代码(' + str(check_links_reason) + '):' + link_url + '\n')
    except Exception as e:
        print('运行出错,请重新运行本程序.错误信息如下:' + '\n')
        print(str(e) + '\n')
        print('用户输入内容:' + '\n')
        print('百度Cookies:' + cookie + '\n')
        print('文件夹名:' + dir_name + '\n')
        print('链接输入:' + '\n' + str(link_url))


if __name__ == '__main__':
    main()
