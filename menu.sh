#!/bin/bash

# =========================================
# 作者: jinqian
# 日期: 2024年11月
# 网站：jinqians.com
# 网站：V2.0
# 描述: 这个脚本用于监控VPS商家库存
# =========================================

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# 配置文件
CONFIG_FILE="config.json"
URLS_FILE="urls.json"
MONITOR_LOG="monitor.log"
INIT_MARK=".initialized"

# 检查监控状态
check_monitor_status() {
    if pgrep -f "python3 monitor.py" > /dev/null; then
        local pid=$(pgrep -f "python3 monitor.py")
        local uptime=$(ps -o etime= -p "$pid")
        echo -e "${GREEN}运行中 (PID: $pid, 运行时间: $uptime)${NC}"
        return 0
    else
        echo -e "${RED}未运行${NC}"
        return 1
    fi
}

# 显示监控详情
show_monitor_details() {
    if check_monitor_status > /dev/null; then
        local pid=$(pgrep -f "python3 monitor.py")
        echo -e "\n${BLUE}=== 监控详情 ===${NC}"
        echo -e "${YELLOW}进程ID: ${NC}$pid"
        echo -e "${YELLOW}运行时间: ${NC}$(ps -o etime= -p "$pid")"
        echo -e "${YELLOW}内存使用: ${NC}$(ps -o rss= -p "$pid" | awk '{print $1/1024 "MB"}')"
        echo -e "${YELLOW}CPU使用率: ${NC}$(ps -o %cpu= -p "$pid")%"
        
        if [ -f "$MONITOR_LOG" ]; then
            echo -e "\n${BLUE}=== 最近日志 ===${NC}"
            tail -n 5 "$MONITOR_LOG"
        fi
        
        if [ -f "$URLS_FILE" ]; then
            local url_count=$(jq 'length' "$URLS_FILE")
            echo -e "\n${BLUE}=== 监控统计 ===${NC}"
            echo -e "${YELLOW}监控商品数: ${NC}$url_count"
        fi
    else
        echo -e "${RED}监控程序未运行${NC}"
    fi
}

# 启动监控
start_monitor() {
    if [ ! -f "$CONFIG_FILE" ]; then
        echo -e "${RED}错误: 未找到配置文件，请先配置Telegram信息${NC}"
        return
    fi

    if [ ! -s "$URLS_FILE" ]; then
        echo -e "${RED}错误: 未找到监控商品，请先添加监控商品${NC}"
        return
    fi

    if pgrep -f "python3 monitor.py" > /dev/null; then
        echo -e "${YELLOW}监控程序已在运行中${NC}"
        return
    fi

    echo -e "${YELLOW}正在启动监控程序...${NC}"
    source venv/bin/activate
    nohup python3 monitor.py >> "$MONITOR_LOG" 2>&1 &
    sleep 3
    
    if pgrep -f "python3 monitor.py" > /dev/null; then
        echo -e "${GREEN}监控程序已成功启动${NC}"
    else
        echo -e "${RED}监控程序启动失败${NC}"
        echo -e "${YELLOW}查看错误日志...${NC}"
        tail -n 5 "$MONITOR_LOG"
    fi
}

# 停止监控
stop_monitor() {
    local pid=$(pgrep -f "python3 monitor.py")
    if [ -n "$pid" ]; then
        echo -e "${YELLOW}正在停止监控程序 (PID: $pid)...${NC}"
        kill $pid
        sleep 2
        if ! pgrep -f "python3 monitor.py" > /dev/null; then
            echo -e "${GREEN}监控程序已停止${NC}"
        else
            echo -e "${RED}监控程序未能正常停止，尝试强制终止...${NC}"
            kill -9 $pid
            echo -e "${GREEN}监控程序已强制终止${NC}"
        fi
    else
        echo -e "${YELLOW}没有运行中的监控程序${NC}"
    fi
}

# 添加URL
add_url() {
    echo -e "\n${YELLOW}请输入产品名称: ${NC}"
    read -r product_name
    
    echo -e "${YELLOW}请输入产品配置（可选，直接回车跳过）: ${NC}"
    read -r product_config
    
    echo -e "${YELLOW}请输入产品URL: ${NC}"
    read -r product_url
    
    if [[ -z "$product_name" || -z "$product_url" ]]; then
        echo -e "${RED}产品名称和URL不能为空${NC}"
        return
    fi
    
    if ! [[ "$product_url" =~ ^https?:// ]]; then
        echo -e "${RED}无效的URL格式${NC}"
        return
    fi

    # 如果文件不存在或为空，创建一个空的JSON对象
    if [ ! -f "$URLS_FILE" ] || [ ! -s "$URLS_FILE" ]; then
        echo '{}' > "$URLS_FILE"
    fi

    # 生成唯一ID（使用时间戳）
    id=$(date +%s)
    
    # 构建JSON数据
    json_data="{\"$id\": {\"名称\": \"$product_name\", \"URL\": \"$product_url\""
    if [ ! -z "$product_config" ]; then
        json_data="$json_data, \"配置\": \"$product_config\""
    fi
    json_data="$json_data}}"

    # 使用jq合并数据
    jq -r ". * $json_data" "$URLS_FILE" > "$URLS_FILE.tmp" && mv "$URLS_FILE.tmp" "$URLS_FILE"
    
    echo -e "${GREEN}添加成功${NC}"
}

# 删除URL
delete_url() {
    if [ ! -s "$URLS_FILE" ]; then
        echo -e "${YELLOW}监控列表为空${NC}"
        return
    fi

    echo -e "\n${YELLOW}当前监控列表：${NC}"
    show_urls
    
    echo -e "\n${YELLOW}请输入要删除的ID：${NC}"
    read -r id
    
    # 检查ID是否存在
    if ! jq -e "has(\"$id\")" "$URLS_FILE" > /dev/null; then
        echo -e "${RED}ID不存在${NC}"
        return 1
    fi

    # 显示要删除的项目信息
    name=$(jq -r ".\"$id\".名称" "$URLS_FILE")
    url=$(jq -r ".\"$id\".URL" "$URLS_FILE")
    
    # 删除指定ID的数据
    jq "del(.\"$id\")" "$URLS_FILE" > "$URLS_FILE.tmp" && mv "$URLS_FILE.tmp" "$URLS_FILE"
    
    echo -e "${GREEN}已删除监控：${NC}"
    echo -e "${BLUE}产品：${NC}$name"
    echo -e "${BLUE}网址：${NC}$url"
}

# 显示所有URL
show_urls() {
    if [ ! -s "$URLS_FILE" ] || [ "$(jq 'length' "$URLS_FILE")" = "0" ]; then
        echo -e "${YELLOW}监控列表为空${NC}"
        return
    fi

    echo -e "\n${YELLOW}当前监控列表：${NC}"
    jq -r 'to_entries[] | "\n\(.key):\n📦 产品：\(.value.名称)\n🔗 链接：\(.value.URL)\(if .value.配置 then "\n⚙️ 配置：\(.value.配置)" else "" end)\n----------------------------------------"' "$URLS_FILE"
}

# 配置Telegram
configure_telegram() {
    echo -e "\n${YELLOW}请输入Telegram Bot Token: ${NC}"
    read -r bot_token
    
    echo -e "${YELLOW}请输入Telegram Chat ID: ${NC}"
    read -r chat_id
    
    echo -e "${YELLOW}请输入检查间隔(秒，默认300): ${NC}"
    read -r interval
    interval=${interval:-300}
    
    cat > "$CONFIG_FILE" << EOF
{
    "bot_token": "$bot_token",
    "chat_id": "$chat_id",
    "check_interval": $interval
}
EOF
    echo -e "${GREEN}配置已保存${NC}"
}

# 查看日志
view_log() {
    if [ -f "$MONITOR_LOG" ]; then
        echo -e "\n${YELLOW}最近的监控日志:${NC}"
        echo -e "${BLUE}====================${NC}"
        tail -n 50 "$MONITOR_LOG"
        echo -e "${BLUE}====================${NC}"
        echo -e "${YELLOW}提示: 按 Ctrl+C 退出日志查看${NC}"
    else
        echo -e "${YELLOW}日志文件不存在${NC}"
    fi
}

# 检查Python环境
check_python() {
    if ! command -v python3 &> /dev/null; then
        echo -e "${YELLOW}正在安装Python3...${NC}"
        if [ -f "/etc/debian_version" ]; then
            apt-get update && apt-get install -y python3 python3-pip python3-venv
        elif [ -f "/etc/redhat-release" ]; then
            yum install -y python3 python3-pip python3-venv
        else
            echo -e "${RED}错误: 无法安装Python3，请手动安装${NC}"
            exit 1
        fi
    else
        # 检查是否安装了python3-venv
        if [ -f "/etc/debian_version" ]; then
            if ! dpkg -l | grep -q python3-venv; then
                echo -e "${YELLOW}正在安装python3-venv...${NC}"
                apt-get update && apt-get install -y python3-venv
            fi
        elif [ -f "/etc/redhat-release" ]; then
            if ! rpm -qa | grep -q python3-venv; then
                echo -e "${YELLOW}正在安装python3-venv...${NC}"
                yum install -y python3-venv
            fi
        fi
    fi
}

# 检查并创建虚拟环境
check_venv() {
    if [ ! -d "venv" ]; then
        echo -e "${YELLOW}正在创建Python虚拟环境...${NC}"
        # 确保python3-venv已安装
        if [ -f "/etc/debian_version" ] && ! dpkg -l | grep -q python3-venv; then
            echo -e "${YELLOW}安装python3-venv...${NC}"
            apt-get update && apt-get install -y python3-venv
        elif [ -f "/etc/redhat-release" ] && ! rpm -qa | grep -q python3-venv; then
            echo -e "${YELLOW}安装python3-venv...${NC}"
            yum install -y python3-venv
        fi
        
        python3 -m venv venv
        if [ $? -eq 0 ]; then
            echo -e "${GREEN}虚拟环境创建成功${NC}"
            # 升级pip
            source venv/bin/activate
            python3 -m pip install --upgrade pip
        else
            echo -e "${RED}虚拟环境创建失败，尝试修复...${NC}"
            rm -rf venv
            if [ -f "/etc/debian_version" ]; then
                apt-get install -y python3-venv
            elif [ -f "/etc/redhat-release" ]; then
                yum install -y python3-venv
            fi
            python3 -m venv venv
            if [ $? -eq 0 ]; then
                echo -e "${GREEN}虚拟环境创建成功${NC}"
                source venv/bin/activate
                python3 -m pip install --upgrade pip
            else
                echo -e "${RED}虚拟环境创建失败，请检查系统环境${NC}"
                exit 1
            fi
        fi
    fi
}

# 激活虚拟环境
activate_venv() {
    if [ -f "venv/bin/activate" ]; then
        source venv/bin/activate
    else
        echo -e "${RED}错误: 虚拟环境不存在${NC}"
        exit 1
    fi
}

# 安装依赖
install_requirements() {
    echo -e "${YELLOW}正在检查并安装依赖...${NC}"
    
    if ! command -v pip3 &> /dev/null; then
        echo -e "${YELLOW}正在安装pip...${NC}"
        if [ -f "/etc/debian_version" ]; then
            apt-get update && apt-get install -y python3-pip
        elif [ -f "/etc/redhat-release" ]; then
            yum install -y python3-pip
        else
            echo -e "${RED}错误: 无法安装pip，请手动安装${NC}"
            exit 1
        fi
    fi

    if [ -f "venv/bin/pip" ]; then
        venv/bin/pip install -r requirements.txt --upgrade
    else
        pip3 install -r requirements.txt --upgrade
    fi

    if [ $? -eq 0 ]; then
        echo -e "${GREEN}依赖安装完成${NC}"
    else
        echo -e "${RED}依赖安装失败${NC}"
        exit 1
    fi
}

# 初始化环境
initialize() {
    # 检查是否已经初始化
    if [ -f "$INIT_MARK" ]; then
        # 只激活虚拟环境
        if [ -f "venv/bin/activate" ]; then
            source venv/bin/activate
            return
        fi
    fi

    # 首次运行，执行完整初始化
    echo -e "${YELLOW}首次运行，正在初始化环境...${NC}"
    check_python
    check_venv
    activate_venv
    install_requirements
    
    # 首次运行配置Telegram
    echo -e "\n${YELLOW}首次运行需要配置Telegram信息${NC}"
    configure_telegram
    
    # 提示添加监控商品
    echo -e "\n${YELLOW}是否现在添加监控商品? [Y/n] ${NC}"
    read -r choice
    if [[ ! "$choice" =~ ^[Nn]$ ]]; then
        add_url
    fi
    
    # 自动启动监控
    if [ -f "$CONFIG_FILE" ] && [ -s "$URLS_FILE" ]; then
        echo -e "\n${YELLOW}正在自动启动监控...${NC}"
        start_monitor
    else
        echo -e "\n${RED}配置不完整，无法自动启动监控${NC}"
        echo -e "${YELLOW}请在主菜单中完成配置后手动启动${NC}"
    fi
    
    # 创建初始化标记文件
    touch "$INIT_MARK"
    echo -e "${GREEN}环境初始化完成${NC}"
    
    # 等待用户确认
    echo -e "\n${YELLOW}按回车键继续...${NC}"
    read
}

# 显示菜单
show_menu() {
    clear
    echo "========================================="
    echo " 作者: jinqian"
    echo " 网站：https://jinqians.com"
    echo " 描述: 这个脚本用于监控VPS商家库存"
    echo "========================================="
    # 显示监控状态和详情
    echo -n "监控状态: "
    check_monitor_status
    if check_monitor_status > /dev/null; then
        local pid=$(pgrep -f "python3 monitor.py")
        echo -e "${BLUE}进程信息: ${NC}PID=$pid, 内存占用=$(ps -o rss= -p "$pid" | awk '{printf "%.1fMB", $1/1024}')"
        if [ -f "$URLS_FILE" ]; then
            local url_count=$(jq 'length' "$URLS_FILE")
            echo -e "${BLUE}监控商品数: ${NC}$url_count"
        fi
    fi
    echo "========================================="
    echo "============== VPS库存监控系统 =============="
    echo "1. 添加监控商品"
    echo "2. 删除监控商品"
    echo "3. 显示所有监控商品"
    echo "4. 配置Telegram信息"
    echo "5. 启动监控"
    echo "6. 停止监控"
    echo "7. 查看监控日志"
    echo "0. 退出"
    echo "===================="
}

# 主循环
main() {
    initialize
    
    while true; do
        show_menu
        echo -e "\n${YELLOW}请选择操作 (0-7): ${NC}"
        read -r choice
        
        case $choice in
            1) add_url ;;
            2) delete_url ;;
            3) show_urls ;;
            4) configure_telegram ;;
            5) start_monitor ;;
            6) stop_monitor ;;
            7) view_log ;;
            0) 
                echo -e "${GREEN}退出程序，监控进程继续在后台运行...${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}无效的选择${NC}"
                ;;
        esac
        
        echo -e "\n${YELLOW}按回车键继续...${NC}"
        read
    done
}

# 运行主程序
main

