# baidu_files_transfers
------------------------------------------
## 百度网盘批量转存工具

​	超过500转存限制后，逐个保存子文件夹文件


## 使用方法

```bash
python3 baidu_files_transfers -u url -p pwd -c cookie -d dir
```

- `url` 是百度网盘的分享地址，如：`https://pan.baidu.com/s/1GfsNzOD6XSj6hUWBnfGojw`
- `p` 是分享提取码，如果没有提取码不需要传这个参数
- `c` 是网页登录到百度网盘后开发者工具获取到的cookie
- `d` 是本人网盘转存文件夹名

由于cookie可以多次使用，因此支持将cookie保存在yaml格式的配置文件中，格式如下：

```yaml
cookie: "XXX=12345;"
```

工具会默认读取当前目录下的`config.yaml`文件，如果不是该文件名，需要使用`-f /path/to/config.yaml`参数指定配置文件路径。使用配置文件指定cookie时，不再需要使用`-c`参数指定cookie了。


### 01 来源介绍
--------------------------------------------------------
转存时，发现有500限制，在github上找个这个脚本，但是不能完全符合需求(子文件夹超过500时，转存失败)，改了改，仅能用于本人需求，有需要可自行修改

[BaiduFilesTransfers_Pro](https://github.com/acheiii/BaiduFilesTransfers_Pro)


### 02 尾巴
--------------------------------------------
有些bug，偶尔转存不了，没时间修，凑合用吧
以后有时间也许会更新
