#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os, sys
import argparse
import json
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


def get_dir_list_recursive(bdstoken, dir='/'):
    # 递归获取云盘目录列表函数
    name_list = []
    curr_name_info_list = get_dir_list(bdstoken, dir)
    for curr_name_info in curr_name_info_list:
        if curr_name_info['isdir'] == 1:
            time.sleep(round(random.uniform(0.001, 2.01), 3))
            curr_name_list = get_dir_list_recursive(bdstoken, curr_name_info['path'])
            name_list += curr_name_list
        else:
            name_list.append(curr_name_info['path'])
    print(len(name_list), dir)
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


def get_share_dir_list_recursive(user_id, share_id, share_dir_name):
    # 递归获取分享链接目录列表函数
    name_list = []
    curr_name_info_list = get_share_dir_list(user_id, share_id, share_dir_name)
    for curr_name_info in curr_name_info_list:
        if curr_name_info['isdir'] == 1:
            time.sleep(round(random.uniform(0.001, 2.01), 3))
            curr_name_list = get_share_dir_list_recursive(user_id, share_id, curr_name_info['path'])
            name_list += curr_name_list
        else:
            name_list.append(curr_name_info['path'])
    print(len(name_list), share_dir_name)
    return name_list


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


def check_link_type(link_list_line):
    # 检测链接种类
    if link_list_line.find('https://pan.baidu.com/s/') >= 0:
        link_type = '/s/'
    return link_type


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
            local_name_list = get_dir_list_recursive(bdstoken, dir='/' + dir_name)
            for i in range(len(local_name_list)):
                local_name_list[i] = local_name_list[i].replace('/' + dir_name, '')
            share_name_list = get_share_dir_list_recursive(user_id_list, shareid_list, '/' + server_filedir)
            print(f'local_name_list: {len(local_name_list)} share_name_list: {len(share_name_list)}')
            print(f'set(local_name_list) - set(share_name_list): {set(local_name_list) - set(share_name_list)}')
            print(f'set(share_name_list) - set(local_name_list): {set(share_name_list) - set(local_name_list)}')
        else:
            print('访问链接返回错误代码(' + str(check_links_reason) + '):' + link_url + '\n')
    except:
        print(traceback.format_exc())


# if __name__ == '__main__':
#     main()
dir_name = 'test'
cookie = 'csrfToken=Ys3aRktUiQ1aWxzUQIacIuhg; newlogin=1; BAIDUID=9BDD1ED0995C1E6F5AF80D8C5F235DD7:FG=1; BAIDUID_BFESS=9BDD1ED0995C1E6F5AF80D8C5F235DD7:FG=1; PANWEB=1; BDCLND=qUjoS8RZJWEKG0PUw4aTuN7IxJmQWaSMf2MApgfADGA%3D; ppfuid=FOCoIC3q5fKa8fgJnwzbE67EJ49BGJeplOzf+4l4EOvDuu2RXBRv6R3A1AZMa49I27C0gDDLrJyxcIIeAeEhD8JYsoLTpBiaCXhLqvzbzmvy3SeAW17tKgNq/Xx+RgOdb8TWCFe62MVrDTY6lMf2GrfqL8c87KLF2qFER3obJGn/QJMAwAPnqrAi45EBm1RGGEimjy3MrXEpSuItnI4KD5Kz0OWHDV87PQYRgEJjruZR4EaoY7dI60LOhq0HnLAJnPxlzwwy/GE1pBh21yFP1qnPhnaNMbTaYSKjVNEhoO/GgLbz7OSojK1zRbqBESR5Pdk2R9IA3lxxOVzA+Iw1TWLSgWjlFVG9Xmh1+20oPSbrzvDjYtVPmZ+9/6evcXmhcO1Y58MgLozKnaQIaLfWRA57rx/FqioD0jqtzyIkIrRSIyIsinQgrPBhVij7Jkrqt7K5jarLOWfD4m/czrcWX3eTNkbS2el0J2+pbyoXJb2gmGOupR9UnwrGA53MVEjRyF55yJEjttlLrWbPAsm9PnhchaSS27hNjpZcLp/IquiTVlyhJ3JXC6kz0QN46eBgz3redDooeLsg11MmhD7jfQaWR5MtmI9nwC4IX4+AvxFueLi0CGaDIQ+QtviUPhX6IF77Dy6yZYDs9YiLioS5IcJpB4bbKxkZr8ZftVYDKWsPOjTvdUJPjdjysFvUHB4mxEED2EBogeW4Pi7LyMotGwkDkjrw7dIOL8eH+akLvTHFYKgGjSgGJg717FXp0wr86a78d24iG0Dtj5SGbPVUixS1vkCXRE9P3n0EwCZJIui90MYHseSGGAb9EEU03OSmbdOT2sun9ZNE1p5JD8fhH17hoY6OdNjT1InhfHXduVLvy2Rt8UlM5usdnb8SHq9GfVomUyetEVgvZpc0nX6wCCfPXXHe2T94hm7JZTBn14F/RznCAxZOh2T1M5RJzFErRK7rlDVpWh8nCIUULCLnjeZ5igGesIfFJE3Z8qG4UZ2aJy8I5nmKWZQG3/B2qm/IBa4AVsxzVOk1vFBmIIXr9vX5IiUZ2pp0YUgVHUwzBuigoNsVQ4+xATvb9rSQRYLYqG48osz3/p1nTSKxY/UzvVhUr4ZyuJhd1Iax1Mu5rZniuyIylJyI7LQa0fQEMhodE4E1Qga6zXe+TcEP3N12POP1kmx5SXPARX5uxyJzAiNILBC8zh7fGfNXOWV37O9g3SrtjD7HHm73k9KjP6c7zyz1OqOlLYK4Zd6grclXRmxxGQV+roQ+0nE4U83L/UBOqmFU2Ekb/vTs/YZwJiVxHg==; BDUSS=UI5aUlvV3JnTTcxbnd5c1VKTjhweVY0RUNNNzY3ODZnV2tSSFVldTIwaklRd1puRVFBQUFBJCQAAAAAAAAAAAEAAAAyiMkb27vc6b~xzb0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMi23mbItt5mQ; BDUSS_BFESS=UI5aUlvV3JnTTcxbnd5c1VKTjhweVY0RUNNNzY3ODZnV2tSSFVldTIwaklRd1puRVFBQUFBJCQAAAAAAAAAAAEAAAAyiMkb27vc6b~xzb0AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAMi23mbItt5mQ; STOKEN=28f15aeab2d65a2f7d71fb03fcd5f478b78cb8633c360fb2bf2d118a65426399; BIDUPSID=9BDD1ED0995C1E6F5AF80D8C5F235DD7; PSTM=1725871838; H_PS_PSSID=60279_60600_60677_60747_60360_60748; BA_HECTOR=a48k202g8k01258h802ga5a5bg32i01jdtdn01u; ZFY=OiYq2MANpOhIzt:BjJdpc0lYAKgsk:BlohBJeGosiU:AWM:C; PANPSC=6040124262865827928%3ACU2JWesajwBSZ62Ew64QLZgtJeEFa7WQuzxdF53m%2FHDMGyfnJI4RSqtfDddEaAbfoz9WvknWWmyaV1QHy3lx29MuAU8GN%2BM3cDLxProYXADVjK%2FWMMIrwy4gEgnMs7UuDtTCc6ZqWjEXfR0R3av0%2B9S%2BWAjVfacz0v29HoOyBxO7W09FU%2BvrLt8NRd7EA5d%2B2fNZfjs7wBY%2FcoIBUQpA2juoAeCl9TBG; ndut_fmt=A21D80571BA680880630A44C54DBA68CE111EF13A9F2E86C83EC8470A6E98EB8; ab_sr=1.0.1_MGFlNDUxNGE2M2NmNmE0ZTZiYzI3MWVlZDAzOThmMzM1MTU3ZjIwNmY4MDkxM2FhMzU1MWEzNTI4MTM3YmU1YTllNjBiODEwOGIyY2M5NmI3NmQ3ZjA4OTk5N2IyNjE1ZDFiYjk5ZWVlYTg2OGYzMmY4NmExNzM5ZjgzZTRiMDhmOTRmNWMyMDMwNWYxNDgwYjJkZmU2OGZkZDhlZTk1ODAxZTNkNWFjMDhlNWFmZDUxMDY1ZWI3M2UyMzliMWNl'
link_url, pass_code = 'https://pan.baidu.com/s/1GfsNzOD6XSj6hUWBnfGojw', '624a'
request_header['Cookie'] = cookie
bdstoken = get_bdstoken()
shareid_list,user_id_list,fs_id_list,server_filedir = check_links(link_url, pass_code, bdstoken)
