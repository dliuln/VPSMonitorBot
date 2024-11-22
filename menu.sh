#!/bin/bash

# =========================================
# 作者: jinqian
# 日期: 2024年11月
# 网站：jinqians.com
# 描述: 这个脚本用于监控VPS商家库存
# =========================================

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
RESET='\033[0m'

URLS_FILE="urls.txt"
LOG_FILE="monitor.log"
CONFIG_FILE="config.json"
VENV_DIR="venv"
PYTHON_CMD="python3"
PID_FILE="monitor.pid"

# 检查并创建虚拟环境
setup_venv() {
    echo "检查虚拟环境..."
    
    # 检查python3-venv是否安装
    if ! dpkg -l | grep -q python3-venv; then
        echo "安装 python3-venv..."
        sudo apt-get update
        sudo apt-get install -y python3-venv python3-pip
    fi
    
    # 创建虚拟环境（如果不存在）
    if [ ! -d "$VENV_DIR" ]; then
        echo "创建虚拟环境..."
        $PYTHON_CMD -m venv $VENV_DIR
    fi
    
    # 激活虚拟环境
    source $VENV_DIR/bin/activate
    
    # 升级pip
    echo "升级pip..."
    pip install --upgrade pip
    
    # 安装依赖
    echo "安装Python依赖..."
    pip install requests "python-telegram-bot>=20.0" asyncio
    
    if ! pip show cloudscraper > /dev/null 2>&1; then
        echo "安装 cloudscraper..."
        pip install cloudscraper
    else
        echo "cloudscraper 已安装!"
    fi
    # 退出虚拟环境
    deactivate
    
    echo "虚拟环境设置完成!"
}

# 检查监控程序状态
check_monitor_status() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            return 0  # 正在运行
        else
            rm -f "$PID_FILE"  # 删除过期的PID文件
        fi
    fi
    return 1  # 没有运行
}

# 启动监控程序
start_monitor() {
    if check_monitor_status; then
        echo "监控程序已经在运行中!"
        return
    fi
    
    # 检查和设置虚拟环境
    setup_venv
    
    # 检查配置文件
    if [ ! -f "$CONFIG_FILE" ]; then
        echo "请先配置Telegram信息!"
        return
    fi
    
    echo "启动监控程序..."
    $VENV_DIR/bin/python monitor.py &
    echo $! > "$PID_FILE"
    echo "监控程序已在后台启动! (PID: $(cat $PID_FILE))"
}

# 停止监控程序
stop_monitor() {
    if [ -f "$PID_FILE" ]; then
        pid=$(cat "$PID_FILE")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "正在停止监控程序..."
            kill "$pid"
            rm -f "$PID_FILE"
            echo "监控程序已停止"
        else
            echo "监控程序未在运行"
            rm -f "$PID_FILE"
        fi
    else
        echo "监控程序未在运行"
    fi
}

# 确保文件存在
touch $URLS_FILE
touch $LOG_FILE

while true; do
    clear
    echo -e "${RED} ========================================= ${RESET}"
    echo -e "${RED} 作者: jinqian ${RESET}"
    echo -e "${RED} 网站：https://jinqians.com ${RESET}"
    echo -e "${RED} 描述: 这个脚本用于监控VPS商家库存 ${RESET}"
    echo -e "${RED} ========================================= ${RESET}"

    echo -e "${CYAN} ============== VPS库存监控系统  ============== ${RESET}"
    
    echo "1. 添加监控网址"
    echo "2. 删除监控网址"
    echo "3. 显示所有监控网址"
    echo "4. 配置Telegram信息"
    echo "5. 启动监控"
    echo "6. 停止监控"
    echo "7. 查看监控状态"
    echo "8. 查看监控日志"
    echo "0. 退出"
    echo "===================="
    
    if check_monitor_status; then
        echo "监控状态: 运行中 (PID: $(cat $PID_FILE))"
    else
        echo "监控状态: 已停止"
    fi
    echo "===================="
    
    read -p "请选择操作 (1-9): " choice
    
    case $choice in
        1)
            read -p "请输入要监控的网址: " url
            echo "$url" >> $URLS_FILE
            echo "添加成功!"
            read -p "按Enter继续..."
            ;;
        2)
            if [ ! -s $URLS_FILE ]; then
                echo "目前没有监控的网址!"
            else
                echo "当前监控的网址:"
                nl $URLS_FILE
                read -p "请输入要删除的行号: " line_num
                sed -i "${line_num}d" $URLS_FILE
                echo "删除成功!"
            fi
            read -p "按Enter继续..."
            ;;
        3)
            if [ ! -s $URLS_FILE ]; then
                echo "目前没有监控的网址!"
            else
                echo "当前监控的网址:"
                nl $URLS_FILE
            fi
            read -p "按Enter继续..."
            ;;
        4)
            read -p "请输入Telegram Bot Token: " bot_token
            read -p "请输入Telegram Chat ID: " chat_id
            read -p "请输入检查间隔时间(秒)[默认300]: " check_interval
            check_interval=${check_interval:-300}
            
            echo "{
                \"bot_token\": \"$bot_token\",
                \"chat_id\": \"$chat_id\",
                \"check_interval\": $check_interval
            }" > $CONFIG_FILE
            echo "Telegram配置已保存!"
            read -p "按Enter继续..."
            ;;
        5)
            start_monitor
            read -p "按Enter继续..."
            ;;
        6)
            stop_monitor
            read -p "按Enter继续..."
            ;;
        7)
            if check_monitor_status; then
                echo "监控程序正在运行 (PID: $(cat $PID_FILE))"
                echo "最近的日志记录:"
                tail -n 5 "$LOG_FILE"
            else
                echo "监控程序未在运行"
            fi
            read -p "按Enter继续..."
            ;;
        8)
            echo "最近的日志记录:"
            tail -n 20 "$LOG_FILE"
            read -p "按Enter继续..."
            ;;
        0)
            read -p "是否要停止监控程序后退出？(y/n): " confirm
            if [ "$confirm" = "y" ] || [ "$confirm" = "Y" ]; then
                stop_monitor
            else
                echo "监控程序将在后台继续运行"
            fi
            echo "感谢使用，再见!"
            exit 0
            ;;
        *)
            echo "无效选择，请重试!"
            read -p "按Enter继续..."
            ;;
    esac
done
