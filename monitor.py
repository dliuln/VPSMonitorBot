import asyncio
import cloudscraper
import time
import logging
import json
import os
import random
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters
)

# 状态定义
CHOOSING, TYPING_URL = range(2)

class VPSMonitor:
    def __init__(self):
        self.urls_file = 'urls.json'  # 改用json文件
        self.config_file = 'config.json'
        self.load_config()
        # 使用 Cloudscraper 初始化
        self.scraper = cloudscraper.create_scraper()
        # 添加状态追踪字典
        self.stock_status = {}  # 存储每个URL的库存状态
        self.notification_count = {}  # 存储每个URL的有货通知次数
        self.first_run = True  # 标记是否是首次运行
        self.product_names = {}  # 存储URL对应的产品名称
        self.product_configs = {}  # 存储URL对应的配置信息
        # 创建Telegram应用
        self.app = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """初始化应用"""
        try:
            self.app = Application.builder().token(self.bot_token).build()
            # 验证 bot token
            await self.app.initialize()
            await self.app.bot.get_me()  # 验证 bot token 是否有效
            self.setup_handlers()
            await self.app.start()
            # 启动轮询
            await self.app.updater.start_polling()
            self.logger.info("Telegram Bot 初始化成功")
        except Exception as e:
            self.logger.error(f"Telegram Bot 初始化失败: {str(e)}")
            raise

    def setup_handlers(self):
        """设置Telegram命令处理器"""
        # 添加命令处理器
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("list", self.list_command))
        self.app.add_handler(CommandHandler("add", self.add_command))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_url))
        self.app.add_handler(CallbackQueryHandler(self.button_click))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /start 命令"""
        keyboard = [
            [
                InlineKeyboardButton("📝 查看监控列表", callback_data='list_urls'),
                InlineKeyboardButton("➕ 添加监控", callback_data='add_url')
            ],
            [
                InlineKeyboardButton("❓ 帮助", callback_data='help')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "👋 欢迎使用 VPS 监控机器人！\n\n"
            "🔍 主要命令：\n"
            "/start - 显示此菜单\n"
            "/list - 查看监控列表\n"
            "/add - 添加监控网址\n"
            "/help - 显示帮助信息\n\n"
            "请选择操作：",
            reply_markup=reply_markup
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /help 命令"""
        help_text = (
            "🤖 VPS监控机器人使用说明：\n\n"
            "📝 主要命令：\n"
            "/start - 显示主菜单\n"
            "/list - 查看监控列表\n"
            "/add - 添加监控网址\n"
            "/help - 显示此帮助信息\n\n"
            "➕ 添加网址：\n"
            "1. 使用 /add 命令\n"
            "2. 直接输入网址（需以http://或https://开头）\n\n"
            "🗑️ 删除网址：\n"
            "1. 使用 /list 命令查看列表\n"
            "2. 点击要删除的网址下方的删除按钮\n\n"
            "💡 提示：确保添加的网址格式正确，包含http(s)://"
        )
        await update.message.reply_text(help_text)

    async def list_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /list 命令"""
        urls_dict = self.load_urls()
        if not urls_dict:
            await update.message.reply_text("📝 当前没有监控的网址")
            return

        await update.message.reply_text("📝 当前监控的网址：")
        for url, name in urls_dict.items():
            keyboard = [[InlineKeyboardButton("🗑️ 删除", callback_data=f'delete_{url}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message = f"📦 产品：{name}\n🔗 链接：{url}"
            if url in self.product_configs:
                message += f"\n⚙️ 配置：{self.product_configs[url].get('配置', '')}"
            await update.message.reply_text(
                message,
                reply_markup=reply_markup
            )

    async def add_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理 /add 命令"""
        context.user_data['adding_url'] = True
        context.user_data['waiting_for'] = 'name'  # 首先等待输入名称
        await update.message.reply_text(
            "请按以下格式分两次输入产品名称和监控网址：\n\n"
            "第一行输入产品名称，例如：\n"
            "Racknerd 2G\n\n"
            "然后等待机器人提示后，再输入URL"
        )

    async def handle_url(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理用户输入的URL"""
        if not context.user_data.get('adding_url'):
            return

        input_text = update.message.text.strip()
        
        # 处理产品名称输入
        if context.user_data.get('waiting_for') == 'name':
            context.user_data['product_name'] = input_text
            context.user_data['waiting_for'] = 'config'
            await update.message.reply_text(
                f"已记录产品名称：{input_text}\n"
                "请输入产品配置信息（可选，直接回车跳过）："
            )
            return

        # 处理配置信息输入
        if context.user_data.get('waiting_for') == 'config':
            context.user_data['product_config'] = input_text if input_text else None
            context.user_data['waiting_for'] = 'url'
            await update.message.reply_text(
                "请输入监控网址（必须以 http:// 或 https:// 开头）："
            )
            return

        # 处理URL输入
        if context.user_data.get('waiting_for') == 'url':
            name = context.user_data.get('product_name')
            config = context.user_data.get('product_config')
            url = input_text

            if not url.startswith(('http://', 'https://')):
                await update.message.reply_text(
                    "❌ URL格式错误！\n"
                    "请确保URL以 http:// 或 https:// 开头\n"
                    "请重新输入URL"
                )
                return

            # 先发送处理中的消息
            processing_message = await update.message.reply_text("⏳ 正在处理...")

            # 保存URL和产品名称
            success, message = self.save_url(name, url, config)
            if not success:
                await processing_message.edit_text(f"❌ {message}")
                # 重置状态
                context.user_data.clear()
                return

            # 立即检查库存状态
            await processing_message.edit_text("🔍 正在检查库存状态...")
            stock_available, error = await self.check_stock(url)
            
            if error:
                await processing_message.edit_text(
                    f"✅ 已添加监控商品：\n"
                    f"📦 产品：{name}\n"
                    f"🔗 链接：{url}\n\n"
                    f"❗ 首次检查状态: {error}\n"
                    "将在下一个检查周期重试\n\n"
                    "使用 /list 命令查看所有监控商品"
                )
            else:
                status = "🟢 有货" if stock_available else "🔴 无货"
                await processing_message.edit_text(
                    f"✅ 已添加监控商品：\n"
                    f"📦 产品：{name}\n"
                    f"🔗 链接：{url}\n\n"
                    f"📊 当前状态: {status}\n\n"
                    "使用 /list 命令查看所有监控商品"
                )

            # 重置状态
            context.user_data.clear()

    async def button_click(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """处理按钮点击"""
        query = update.callback_query
        await query.answer()  # 确认收到回调

        try:
            if query.data == 'list_urls':
                urls_dict = self.load_urls()
                if not urls_dict:
                    await query.message.reply_text("📝 当前没有监控的网址")
                    return

                await query.message.reply_text("📝 当前监控的网址：")
                for url, name in urls_dict.items():
                    keyboard = [[InlineKeyboardButton("🗑️ 删除", callback_data=f'delete_{url}')]]
                    reply_markup = InlineKeyboardMarkup(keyboard)
                    message = f"📦 产品：{name}\n🔗 链接：{url}"
                    if url in self.product_configs:
                        message += f"\n⚙️ 配置：{self.product_configs[url].get('配置', '')}"
                    await query.message.reply_text(
                        message,
                        reply_markup=reply_markup
                    )

            elif query.data == 'add_url':
                context.user_data['adding_url'] = True
                context.user_data['waiting_for'] = 'name'  # 首先等待输入名称
                await query.message.reply_text(
                    "请按以下格式分两次输入产品名称和监控网址：\n\n"
                    "第一行输入产品名称，例如：\n"
                    "Racknerd 2G\n\n"
                    "然后等待机器人提示后，再输入URL"
                )

            elif query.data == 'help':
                help_text = (
                    "🤖 VPS监控机器人使用说明：\n\n"
                    "📝 主要命令：\n"
                    "/start - 显示主菜单\n"
                    "/list - 查看监控列表\n"
                    "/add - 添加监控网址\n"
                    "/help - 显示此帮助信息\n\n"
                    "➕ 添加网址：\n"
                    "1. 使用 /add 命令\n"
                    "2. 直接输入网址（需以http://或https://开头）\n\n"
                    "🗑️ 删除网址：\n"
                    "1. 使用 /list 命令查看列表\n"
                    "2. 点击要删除的网址下方的删除按钮\n\n"
                    "💡 提示：确保添加的网址格式正确，包含http(s)://"
                )
                await query.message.reply_text(help_text)

            elif query.data.startswith('delete_'):
                url = query.data[7:]  # 删除'delete_'前缀
                success, message = self.remove_url(url)
                if success:
                    await query.message.reply_text(f"✅ 已删除监控网址：\n{url}")
                else:
                    await query.message.reply_text(f"❌ {message}")

        except Exception as e:
            self.logger.error(f"处理按钮点击时出错: {str(e)}")
            await query.message.reply_text("❌ 操作失败，请重试")

    async def check_stock(self, url):
        """检查单个URL的库存状态"""
        try:
            # 添加随机延迟
            await asyncio.sleep(random.uniform(1, 3))
            
            # 设置请求头
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.9',
                'Accept-Encoding': 'gzip, deflate, br',
                'Cache-Control': 'no-cache',
                'Pragma': 'no-cache',
                'Sec-Ch-Ua': '"Not_A Brand";v="8", "Chromium";v="120", "Google Chrome";v="120"',
                'Sec-Ch-Ua-Mobile': '?0',
                'Sec-Ch-Ua-Platform': '"Windows"',
                'Sec-Fetch-Dest': 'document',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'none',
                'Sec-Fetch-User': '?1',
                'Upgrade-Insecure-Requests': '1'
            }
            
            response = self.scraper.get(url, headers=headers, timeout=30)
            if response.status_code == 200:
                # 检查页面内容是否包含缺货关键词
                out_of_stock_keywords = ['sold out', 'out of stock', '缺货', '售罄', '补货中']
                content = response.text.lower()
                is_out_of_stock = any(keyword in content for keyword in out_of_stock_keywords)
                return not is_out_of_stock, None
            else:
                return None, f"请求失败 (HTTP {response.status_code})"
        except Exception as e:
            return None, f"检查失败: {str(e)}"

    def load_urls(self):
        """从JSON文件加载URL数据"""
        urls_dict = {}
        try:
            try:
                with open(self.urls_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for id_str, info in data.items():
                        url = info.get('URL', '')
                        if url:
                            urls_dict[url] = info.get('名称', '')
                            self.product_names[url] = info.get('名称', '')
                            if info.get('配置'):
                                self.product_configs[url] = {'配置': info.get('配置')}
                    
                    self.logger.info(f"成功加载 {len(urls_dict)} 个URL")
            except FileNotFoundError:
                self.logger.info("URL文件不存在，将创建新文件")
                with open(self.urls_file, 'w', encoding='utf-8') as f:
                    json.dump({}, f, ensure_ascii=False, indent=4)
            
            return urls_dict
                    
        except Exception as e:
            self.logger.error(f"加载URL文件时出错: {str(e)}")
            return {}

    def save_url(self, name, url, config=None):
        """保存URL到JSON文件"""
        try:
            # 读取现有数据
            try:
                with open(self.urls_file, 'r') as f:
                    data = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                data = {}
            
            # 检查URL是否已存在
            url_exists = False
            existing_id = None
            for id_str, info in data.items():
                if info.get('URL') == url:
                    url_exists = True
                    existing_id = id_str
                    break
            
            if url_exists:
                # 更新现有记录
                data[existing_id] = {
                    "名称": name,
                    "URL": url,
                    "配置": config if config else ""
                }
            else:
                # 添加新记录
                new_id = str(len(data) + 1)
                data[new_id] = {
                    "名称": name,
                    "URL": url,
                    "配置": config if config else ""
                }
            
            # 保存到文件
            with open(self.urls_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            
            # 更新内存中的数据
            self.product_names[url] = name
            if config:
                self.product_configs[url] = {'配置': config}
            
            return True, "保存成功"
        except Exception as e:
            self.logger.error(f"保存URL失败: {str(e)}")
            return False, f"保存失败: {str(e)}"

    def remove_url(self, url):
        """从JSON文件中删除URL"""
        try:
            # 读取现有数据
            with open(self.urls_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 查找并删除URL
            target_id = None
            for id_str, info in data.items():
                if info.get('URL') == url:
                    target_id = id_str
                    break
            
            if target_id:
                del data[target_id]
                
                # 保存更新后的数据
                with open(self.urls_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
                
                # 清理内存中的数据
                if url in self.product_names:
                    del self.product_names[url]
                if url in self.product_configs:
                    del self.product_configs[url]
                if url in self.stock_status:
                    del self.stock_status[url]
                if url in self.notification_count:
                    del self.notification_count[url]
                
                return True, "删除成功"
            else:
                return False, "未找到该URL"
                
        except Exception as e:
            self.logger.error(f"删除URL失败: {str(e)}")
            return False, f"删除失败: {str(e)}"

    async def send_telegram_notification(self, message):
        """发送Telegram通知"""
        try:
            if not self.app:
                self.logger.error("Telegram Bot 未初始化")
                return
                
            await self.app.bot.send_message(
                chat_id=self.chat_id,
                text=message
            )
            self.logger.info("Telegram 通知发送成功")
        except Exception as e:
            self.logger.error(f"发送Telegram通知失败: {str(e)}")

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.bot_token = config['bot_token']
                self.chat_id = config['chat_id']
                self.check_interval = config.get('check_interval', 300)
        except Exception as e:
            self.logger.error(f"加载配置文件失败: {str(e)}")
            exit(1)

    async def monitor(self):
        """主监控循环"""
        try:
            # 初始化 Telegram Bot
            await self.initialize()
            
            # 发送启动通知
            await self.send_telegram_notification(
                "🚀 VPS监控程序已启动\n"
                f"⏰ 当前检查间隔：{self.check_interval}秒\n\n"
                "💡 使用 /start 开始操作，/help 查看帮助\n\n\n"
                "🔄 正在进行启动检查..."
            )
            
            self.logger.info("开始监控...")
            
            # 启动时进行初始检查
            urls_dict = self.load_urls()
            if urls_dict:
                await self.send_telegram_notification("🔄 正在进行启动检查...")
                for url, name in urls_dict.items():
                    try:
                        stock_available, error = await self.check_stock(url)
                        if error:
                            await self.send_telegram_notification(
                                f"📦 产品：{name}\n"
                                f"🔗 链接：{url}\n"
                                f"❗ 检查失败: {error}"
                            )
                        else:
                            status = "🟢 有货" if stock_available else "🔴 无货"
                            message = (
                                f"📦 产品：{name}\n"
                                f"🔗 链接：{url}\n"
                            )
                            if url in self.product_configs:
                                config_info = self.product_configs[url].get('配置', '')
                                message += f"⚙️ 配置：{config_info}\n"
                            message += f"📊 当前状态：{status}"
                            await self.send_telegram_notification(message)
                            # 记录初始状态
                            self.stock_status[url] = stock_available
                            self.notification_count[url] = 3  # 设置为3，这样就不会再发送后续通知
                    except Exception as e:
                        self.logger.error(f"初始检查URL {url} 时出错: {str(e)}")
                        continue
                
                await self.send_telegram_notification("✅ 启动检查完成")
            
            # 保持程序运行
            while True:
                try:
                    # 加载URL列表
                    urls_dict = self.load_urls()
                    if not urls_dict:
                        self.logger.info("没有要监控的URL")
                        await asyncio.sleep(self.check_interval)
                        continue

                    for url, name in urls_dict.items():
                        try:
                            stock_available, error = await self.check_stock(url)
                            
                            # 状态发生变化时发送通知
                            if url not in self.stock_status:
                                self.stock_status[url] = stock_available
                                self.notification_count[url] = 0
                            elif stock_available != self.stock_status[url]:
                                status = "🟢 有货" if stock_available else "🔴 无货"
                                message = (
                                    f"📦 产品：{name}\n"
                                    f"🔗 链接：{url}\n"
                                )
                                if url in self.product_configs:
                                    config_info = self.product_configs[url].get('配置', '')
                                    message += f"⚙️ 配置：{config_info}\n"
                                message += f"📊 当前状态：{status}"
                                await self.send_telegram_notification(message)
                                self.stock_status[url] = stock_available
                                self.notification_count[url] = 0 if not stock_available else 1  # 如果有货，开始计数
                            elif stock_available and not self.stock_status[url]:
                                message = (
                                    f"📦 产品：{name}\n"
                                    f"🔗 链接：{url}\n"
                                )
                                if url in self.product_configs:
                                    config_info = self.product_configs[url].get('配置', '')
                                    message += f"⚙️ 配置：{config_info}\n"
                                message += "📊 状态：🟢 现在有货了！"
                                await self.send_telegram_notification(message)
                                self.stock_status[url] = True
                                self.notification_count[url] = 1  # 开始计数连续通知
                            # 状态从有货变为无货时
                            elif not stock_available and self.stock_status[url]:
                                message = (
                                    f"📦 产品：{name}\n"
                                    f"🔗 链接：{url}\n"
                                )
                                if url in self.product_configs:
                                    config_info = self.product_configs[url].get('配置', '')
                                    message += f"⚙️ 配置：{config_info}\n"
                                message += "📊 状态：🔴 已经无货"
                                await self.send_telegram_notification(message)
                                self.stock_status[url] = False
                                self.notification_count[url] = 0  # 重置有货通知计数
                            # 持续有货且未达到3次通知限制时
                            elif stock_available and self.stock_status[url] and self.notification_count[url] < 3:
                                message = (
                                    f"📦 产品：{name}\n"
                                    f"🔗 链接：{url}\n"
                                )
                                if url in self.product_configs:
                                    config_info = self.product_configs[url].get('配置', '')
                                    message += f"⚙️ 配置：{config_info}\n"
                                message += f"📊 状态：🟢 仍然有货 (通知 {self.notification_count[url] + 1}/3)"
                                await self.send_telegram_notification(message)
                                self.notification_count[url] += 1

                        except Exception as e:
                            self.logger.error(f"检查URL {url} 时出错: {str(e)}")
                            continue

                    await asyncio.sleep(self.check_interval)
                except Exception as e:
                    self.logger.error(f"监控循环出错: {str(e)}")
                    await asyncio.sleep(60)  # 出错后等待1分钟再继续

        except Exception as e:
            self.logger.error(f"监控程序出错: {str(e)}")
            raise
        finally:
            # 清理资源
            try:
                if self.app:
                    await self.app.updater.stop()
                    await self.app.stop()
                    await self.app.shutdown()
            except Exception as e:
                self.logger.error(f"关闭应用时出错: {str(e)}")

async def main():
    """主程序入口"""
    # 配置日志记录
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('monitor.log', encoding='utf-8'),
            logging.StreamHandler()
        ]
    )
    logger = logging.getLogger(__name__)

    try:
        monitor = VPSMonitor()
        await monitor.monitor()
    except KeyboardInterrupt:
        logger.info("程序被用户中断")
    except Exception as e:
        logger.error(f"程序发生错误: {str(e)}")
        raise

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n程序已停止")
    except Exception as e:
        print(f"程序发生错误: {str(e)}")
