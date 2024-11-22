# VPSMonitorBot
VPSMonitorBot 是一个基于 Telegram 的网站库存监控工具，旨在帮助用户实时监控指定网站的商品供货情况。通过此工具，您可以监控多个VPS网站或商品页面的库存状态，当某个商品上架，系统会自动通过 Telegram 发送通知。特别适合需要监控VPS是否有货的用户，确保不会错过重要的购买机会。

## 演示机器人
[@JQ_VPSMonitorBot](t.me/JQ_VPSMonitorBot)

## 核心功能

- **VPS 库存监控**
- **Telegram 通知**
- **自定义检查间隔**
- **简单的命令行管理**

## 技术架构

本项目使用 Python 编写，结合 `cloudscraper` 绕过反爬虫机制，使用 `requests` 库进行网站商品库存检测，并通过 `python-telegram-bot` 库与 Telegram 进行消息通知。项目使用虚拟环境管理 Python 依赖，确保环境隔离与兼容性。

## 使用
```shell
apt install git -y
git clone https://github.com/jinqians/VPSMonitorBot.git && cd VPSMonitorBot && chmod +x menu.sh
./menu.sh
```

## 菜单示例
```bash
 ========================================= 
 作者: jinqian 
 网站：https://jinqians.com 
 描述: 这个脚本用于监控VPS商家库存 
 ========================================= 
 ============== VPS库存监控系统  ============== 
1. 添加监控网址
2. 删除监控网址
3. 显示所有监控网址
4. 配置Telegram信息
5. 启动监控
6. 停止监控
7. 查看监控状态
8. 查看监控日志
0. 退出
====================
监控状态: 运行中 (PID: 23395)
====================
请选择操作 (0-8): 
```
