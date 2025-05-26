# playwright_login.py
from playwright.sync_api import sync_playwright

def manual_login_and_save():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # 打开真浏览器
        context = browser.new_context()

        page = context.new_page()
        page.goto("https://www.zhihu.com")

        print("请手动登录知乎账户...")

        input("登录完成后请按回车继续：")

        # 保存登录状态
        context.storage_state(path="playwright_auth/storage.json")
        print("✅ 登录状态已保存到 playwright_auth/storage.json")

        browser.close()

manual_login_and_save()
