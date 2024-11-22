import asyncio
import cloudscraper
import time
import logging
import json
import os
from datetime import datetime
from telegram import Bot
from telegram.error import TelegramError

# 配置日志
logging.basicConfig(
    filename='monitor.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class VPSMonitor:
    def __init__(self):
        self.urls_file = 'urls.txt'
        self.config_file = 'config.json'
        self.load_config()
        self.setup_telegram()
        # 使用 Cloudscraper 初始化
        self.scraper = cloudscraper.create_scraper()

    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r') as f:
                config = json.load(f)
                self.bot_token = config['bot_token']
                self.chat_id = config['chat_id']
                self.check_interval = int(config['check_interval'])
        except FileNotFoundError:
            logging.error("配置文件不存在！请先运行菜单配置Telegram信息。")
            exit(1)
        except json.JSONDecodeError:
            logging.error("配置文件格式错误！")
            exit(1)
        except KeyError as e:
            logging.error(f"配置文件缺少必要的键：{str(e)}")
            exit(1)

    def setup_telegram(self):
        """设置Telegram机器人"""
        try:
            self.bot = Bot(token=self.bot_token)
        except Exception as e:
            logging.error(f"Telegram配置错误：{str(e)}")
            exit(1)

    async def verify_bot(self):
        """验证Bot配置"""
        try:
            await self.bot.get_me()
            return True
        except Exception as e:
            logging.error(f"Telegram Bot验证失败：{str(e)}")
            return False

    def read_urls(self):
        """读取监控URL列表"""
        try:
            with open(self.urls_file, 'r') as f:
                return [url.strip() for url in f.readlines() if url.strip()]
        except FileNotFoundError:
            logging.error("URLs文件不存在")
            return []

    def check_stock(self, url):
        """检查库存状态"""
        try:
            response = self.scraper.get(url, timeout=15)
            response.raise_for_status()
            
            # 根据具体页面调整库存判断逻辑
            out_of_stock_keywords = ['缺货', '售罄', 'Out of Stock', 'Sold Out']
            page_content = response.text.lower()
            
            for keyword in out_of_stock_keywords:
                if keyword.lower() in page_content:
                    return False
            return True
            
        except cloudscraper.exceptions.CloudflareChallengeError as e:
            logging.error(f"Cloudflare 检查失败 {url}: {str(e)}")
            return None
        except Exception as e:
            logging.error(f"检查网址 {url} 时发生错误: {str(e)}")
            return None

    async def send_telegram_notification(self, message):
        """发送Telegram通知"""
        try:
            await self.bot.send_message(
                chat_id=self.chat_id,
                text=message,
                parse_mode='HTML'
            )
            logging.info(f"Telegram通知已发送: {message}")
        except Exception as e:
            logging.error(f"发送Telegram通知时发生错误: {str(e)}")

    async def monitor(self):
        """主监控循环"""
        logging.info("监控程序启动")
        
        # 验证Bot配置
        if not await self.verify_bot():
            logging.error("Bot验证失败，程序退出")
            return

        await self.send_telegram_notification(
            "🚀 VPS监控程序已启动\n"
            f"当前检查间隔：{self.check_interval}秒"
        )
        
        while True:
            urls = self.read_urls()
            if not urls:
                logging.warning("没有要监控的网址")
                await asyncio.sleep(self.check_interval)
                continue

            for url in urls:
                stock_status = self.check_stock(url)
                
                if stock_status is True:
                    message = (
                        f"🎉 <b>发现有货!</b>\n"
                        f"🔗 网址: {url}\n"
                        f"⏰ 时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    )
                    await self.send_telegram_notification(message)
                elif stock_status is False:
                    logging.info(f"网址 {url} 当前无货")
                else:
                    logging.warning(f"检查网址 {url} 失败")

            await asyncio.sleep(self.check_interval)

async def main():
    try:
        monitor = VPSMonitor()
        await monitor.monitor()
    except KeyboardInterrupt:
        logging.info("程序被用户中断")
        print("\n程序已停止")
    except Exception as e:
        logging.error(f"程序发生错误: {str(e)}")
        print(f"程序发生错误: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
