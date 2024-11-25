# VPSMonitorBot
VPSMonitorBot 是一个基于 Telegram 的网站库存监控工具，旨在帮助用户实时监控指定网站的商品供货情况。通过此工具，您可以监控多个VPS网站或商品页面的库存状态，当某个商品上架，系统会自动通过 Telegram 发送通知。特别适合需要监控VPS是否有货的用户，确保不会错过重要的购买机会。

## 演示机器人
[@JQ_VPSMonitorBot](https://t.me/JQ_VPSMonitorBot)

## 核心功能

- **VPS 库存监控**
  - 实时监控多个网站的库存状态
  - 启动时自动检查所有监控商品的状态
  - 支持自定义检查间隔
  - 智能检测商品是否缺货

- **Telegram 通知**
  - 即时库存状态变化通知
  - 友好的交互式命令界面
  - 支持按钮式操作
  - 分步式添加监控商品

- **管理功能**
  - 查看所有监控商品列表
  - 一键添加/删除监控商品
  - 实时查看监控状态
  - 查看运行日志

## 技术架构

本项目使用 Python 编写，结合以下技术：
- `python-telegram-bot`: 提供 Telegram Bot API 交互
- `requests`: 进行网站商品库存检测
- 虚拟环境：管理 Python 依赖，确保环境隔离与兼容性

## 安装使用

### 快速开始
```shell
apt install git -y
git clone https://github.com/jinqians/VPSMonitorBot.git && cd VPSMonitorBot && chmod +x menu.sh
./menu.sh
```

### Telegram Bot 命令
- `/start` - 显示主菜单
- `/list` - 查看监控列表
- `/add` - 添加监控商品
- `/help` - 显示帮助信息

### 添加监控商品
1. 使用 `/add` 命令或点击主菜单中的"添加监控"按钮
2. 按提示输入商品名称（例如：Racknerd 2G）
3. 输入商品URL（必须以 http:// 或 https:// 开头）
4. 系统会立即检查商品状态并通知您

#### 演示
![](http://vps.jinqians.com/wp-content/uploads/2024/11/112501.png)
![](http://vps.jinqians.com/wp-content/uploads/2024/11/112502.png)

## 菜单功能
```bash
=========================================
监控状态: 运行中 (PID:*** , 运行时间:       00:00)
进程信息: PID=:***, 内存占用=:***MB
监控商品数: ???
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

## 配置说明

### config.json
```json
{
    "bot_token": "YOUR_BOT_TOKEN",
    "chat_id": "YOUR_CHAT_ID",
    "check_interval": 300
}
```
- `bot_token`: Telegram Bot 的 API Token
- `chat_id`: 接收通知的 Telegram 聊天 ID
- `check_interval`: 检查间隔（秒）

### urls.txt
每行一个监控商品，格式：
```
商品名称
商品URL
```

## 更新日志

### v2.0.0
- 添加启动时自动检查所有商品状态功能
- 改进商品添加流程，采用分步输入方式
- - Telegram Bot 集成
- 优化通知消息格式
- 改进错误处理机制

### v1.0.0
- 初始版本发布
- 基础监控功能
- 命令行管理界面

## 注意事项
1. 确保您的网络环境能够访问 Telegram
2. 监控URL必须以 http:// 或 https:// 开头
3. 建议将检查间隔设置在合理范围内（建议不低于300秒）
4. 程序运行时会自动创建日志文件
