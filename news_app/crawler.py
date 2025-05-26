from openai import OpenAI
import requests
from bs4 import BeautifulSoup
import time
import re
import json
from collections import defaultdict
import os
from my_wordcloud import creat_wordcloud
import matplotlib.pyplot as plt
from playwright.sync_api import sync_playwright 
from urllib.parse import quote
from selenium.webdriver.chrome.options import Options
from selenium import webdriver
import urllib3
import os
import shutil
from draw_pyvis import generate_quadruple_graph_html_with_link
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)



# ✅ 替换成你的 DeepSeek API Key
DEEPSEEK_API_KEY = " "

# ✅ 初始化 DeepSeek API 客户端
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com"
)

def print_test(msg):
    print(f"测试：{msg}")
    return msg

def safe_request(url, headers=None, timeout=10):
    try:
        headers = headers or {"User-Agent": "Mozilla/5.0"}
        response = requests.get(url, headers=headers, timeout=timeout)
        response.encoding = response.apparent_encoding
        if response.status_code == 200:
            return response.text
        return None
    except Exception as e:
        print(f"❌ 请求失败: {url} - {e}")
        return None

def extract_text_from_tags(soup, selectors):
    for selector in selectors:
        tag = soup.select_one(selector)
        if tag:
            paragraphs = tag.find_all('p')
            text = '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))
            if len(text) > 100:
                return text
    return ""

# 凤凰
def get_fenghuang_news_body(url):
    """提取凤凰新闻正文"""
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code != 200:
            return ""

        soup = BeautifulSoup(response.text, "html.parser")
        content_divs = soup.select("div.index_smallFont_3Pwv1, div.index_text_TwFCV, div.articleText")
        time_tag = soup.select_one("span.time-3vNLpJrC") or soup.select_one("span.time") or soup.find("time")
        pub_time = time_tag.get_text(strip=True) if time_tag else ""

        content = ""
        for div in content_divs:
            paragraphs = div.find_all("p")
            for p in paragraphs:
                text = p.get_text(strip=True)
                if text:
                    content += text + "\n"

        return content.strip(), pub_time
    except Exception as e:
        print(f"❌ 正文提取失败: {url} - {e}")
        return ""

def get_fenghuang_news(keyword: str, max_results: int = 10):
    """抓取凤凰新闻，与百度新闻字段格式统一"""
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        
        search_url = f"https://so.ifeng.com/?q={keyword}"
        page.goto(search_url)
        page.wait_for_timeout(3000)
        
        soup = BeautifulSoup(page.content(), "html.parser")
        browser.close()

    news_list = soup.select("ul.news-stream-basic-news-list li.news_item")

    for li in news_list:
        a_tag = li.select_one("h2 a")
        if not a_tag or not a_tag.get("href"):
            continue

        title = a_tag.get_text(strip=True).replace("\xa0", "")
        url = a_tag.get("href")
        if url.startswith("//"):
            url = "https:" + url

        # 🔍 进入详情页获取正文和时间
        body,time = get_fenghuang_news_body(url)

        results.append({
            "title": title,
            "abstract": "",         # 可后续补摘要
            "link": url,
            "platform": "凤凰网",
            "time": time,
            "body": body
        })

        if len(results) >= max_results:
            break

    return results
# 新浪
def get_sina_news_body(url):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        res = requests.get(url, headers=headers, timeout=10)
        res.encoding = 'utf-8'
        soup = BeautifulSoup(res.text, 'html.parser')
        possible_tags = [
            'div.article', 'div.main-content', 'div#artibody', 'div.article-content-left'
        ]
        for tag in possible_tags:
            content = soup.select_one(tag)
            if content:
                paragraphs = content.find_all('p')
                text = '\n'.join(p.get_text().strip() for p in paragraphs if p.get_text().strip())
                if len(text) > 100:
                    return text
        return "⚠️ 正文解析失败"
    except Exception as e:
        return f"⚠️ 错误：{str(e)}"

def get_sina_news(keyword, pages=1):
    headers = {"User-Agent": "Mozilla/5.0"}
    results = []
    for page in range(1, pages + 1):
        url = f"https://search.sina.com.cn/?q={keyword}&c=news&range=all&num=20&page={page}"
        print(f"正在抓取第 {page} 页: {url}")
        
        response = requests.get(url, headers=headers, timeout=10)
        response.encoding = 'utf-8'
        soup = BeautifulSoup(response.text, 'html.parser')
        articles = soup.select('div.box-result.clearfix')
        
        if not articles:
            print("⚠️ 未抓到新闻，可能被限制访问或关键词无结果。")
            continue
        for article in articles:
            title_tag = article.select_one('h2 a')
            abstract_tag = article.select_one('p.content')
            time_tag = article.select_one('span.fgray_time')
            if title_tag and abstract_tag and time_tag:
                news_url = title_tag['href']
                news_body = get_sina_news_body(news_url)
                results.append({
                    'title': title_tag.text.strip(),
                    'link': news_url,
                    'abstract': abstract_tag.text.strip(),
                    'time': time_tag.text.strip(),
                    'body': news_body,
                    'platform': '新浪新闻'
                })
        time.sleep(1)
    return results
# 百度
def resolve_real_url(baidu_url):
    """跳转百度中转链接，获取真实新闻URL"""
    try:
        resp = requests.get(baidu_url, headers={"User-Agent": "Mozilla/5.0"},
                            verify=False, timeout=10, allow_redirects=True)
        return resp.url
    except Exception as e:
        print(f"❌ 跳转失败: {e}")
        return baidu_url

def get_baidu_news_body(url):
    """抓取新闻正文"""
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=10, verify=False)
        resp.encoding = 'utf-8'
        soup = BeautifulSoup(resp.text, 'html.parser')

        candidate_selectors = [
            'div.article-content',
            'div.article-body',
            'div.post_text',
            'div#artibody',
            'div#content',
            'div.main-content',
            'div#main-content',
            'div.show_text',
            'div.yd_text',
        ]

        for selector in candidate_selectors:
            content_div = soup.select_one(selector)
            if content_div:
                paragraphs = content_div.find_all('p')
                if paragraphs:
                    return '\n'.join(p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True))

        # 兜底方案
        all_paragraphs = soup.find_all('p')
        text = '\n'.join(p.get_text(strip=True) for p in all_paragraphs if p.get_text(strip=True))
        return text if len(text) > 100 else ''
    except Exception as e:
        print(f"❌ 抓正文失败: {url} -> {e}")
        return ''

def get_baidu_news_with_selenium(keyword, pages=1):
    """使用Selenium抓取百度新闻"""
    # 设置Selenium不显示浏览器界面
    chrome_options = Options()
    chrome_options.add_argument("--headless")  # 不打开浏览器
    chrome_options.add_argument("--disable-gpu")  # 禁用GPU
    driver = webdriver.Chrome(options=chrome_options)

    results = []
    for page in range(pages):
        pn = page * 10
        query = quote(keyword)
        url = f"https://www.baidu.com/s?tn=news&rtt=1&bsst=1&wd={query}&pn={pn}"
        print(f"🔍 抓取第 {page + 1} 页: {url}")

        driver.get(url)
        time.sleep(2)  # 等待页面加载

        # 获取页面内容
        soup = BeautifulSoup(driver.page_source, 'html.parser')

        # 选择器
        news_blocks = soup.select("div.result") + soup.select("div.result-op")
        for block in news_blocks:
            a_tag = block.select_one('h3 a')
            summary = block.select_one('div.c-abstract') or block.select_one('div.c-span18 p')
            time_tag = block.select_one('span.c-color-gray2') or block.select_one('span.c-color-gray')
            if not a_tag or not a_tag.get('href'):
                continue

            baidu_link = a_tag['href']
            real_url = resolve_real_url(baidu_link)

            body = get_baidu_news_body(real_url)
            if not body:
                continue

            results.append({
                "title": a_tag.get_text(strip=True),
                "abstract": summary.get_text(strip=True) if summary else "",
                "link": real_url,
                "platform": real_url.split('/')[2],
                "time": time_tag.get_text(strip=True) if time_tag else "",
                "body": body,
                'platform': '百度新闻'
            })
            time.sleep(0.5)  # 避免过快

        time.sleep(1)  # 翻页延时
    driver.quit()
    return results

#公共方法
#摘要
def summarize_news(news_body: str) -> list[str]:
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {
                "role": "system",
                "content": (
                    "你是一个擅长中文新闻总结和分类的助手。"
                    "请根据用户提供的新闻内容，"
                    "返回一个包含两个部分的回答："
                    "1. 新闻摘要（简洁，不超过25字），"
                    "2. 新闻分类（通知、投诉、表扬、处罚、建议、其他），"
                    "格式为：[摘要内容, 新闻分类]"
                    "新闻分类请严格按照六类进行分类：“通知、投诉、表扬、处罚、建议、其他”，不允许任何其他分类！"
                    
                )
            },
            {"role": "user", "content": f"请总结并分类以下新闻内容：{news_body}"}
        ],
        stream=False
    )
    raw_text = response.choices[0].message.content.strip()
    # 这里尝试解析成列表
    # 简单处理，去掉中英文括号和空格
    matched = re.findall(r'[\u4e00-\u9fa5a-zA-Z0-9。，、,.]+', raw_text)
    
    if len(matched) >= 2:
        return [matched[0], matched[1]]
    else:
        # 如果解析失败，返回全文摘要，分类默认未分类
        return [raw_text, "未分类"]
#提取四元组
def extract_quadruples(news_body: str):
    prompt = f"""请阅读以下新闻内容，抽取“实体-事件-实体-情感”的四元组,要额外注意负面消息或负面情绪。
每个四元组反映一个事实：
- 实体1 是动作或事件的发出者（如企业、政府、人物等）；
- 事件是行为或状态（如“发布”“批评”“调查”）；
- 实体2 是被影响的对象（如产品、政策、人物等）；
- 情感为正面、负面或中性，反映舆论对此事件的态度。

请使用以下格式逐行输出多个四元组（每行一个）：
(实体1, 事件, 实体2, 情感)

示例：
(华为, 发布, Pura70, 正面)
(小米, 被批评, 产品质量, 负面)

请不要添加其他解释性内容，只返回括号中的结构。

新闻内容如下：
{news_body}
    """
    response = client.chat.completions.create(
        model="deepseek-chat",
        messages=[
            {"role": "system", "content": "你是一个擅长中文信息抽取的助手。"},
            {"role": "user", "content": prompt}
        ],
        stream=False
    )
    content = response.choices[0].message.content
    
    if re.search(r'[\x00-\x08\x0B\x0C\x0E-\x1F\uFFFD]', content):
        return ""
    
    return content
#解析四元组
def parse_quadruples(quadruple_text: str|None):
    pattern = re.compile(r'\((.+?),\s*(.+?),\s*(.+?),\s*(.+?)\)')
    matches = pattern.findall(quadruple_text)

    parsed = []
    for ent1, event, ent2, sentiment in matches:
        parsed.append({
            "实体1": ent1.strip(),
            "事件": event.strip(),
            "实体2": ent2.strip(),
            "情感": sentiment.strip()
        })
    return parsed
#名称处理
def safe_filename(title, max_length=50):
    filename = re.sub(r'[\\/*?:"<>|]', '_', title)
    filename = filename.strip().replace(' ', '_')
    return filename[:max_length]
#保存为json
def save_news_json_with_quadruples(news, summary,type, quadruples, output_dir="json_file"):
    os.makedirs(output_dir, exist_ok=True)
    data = {
        "title": news['title'],
        "link": news['link'],
        "time": news['time'],
        "platform": news['platform'],
        "type": type,
        "摘要": summary,
        "四元组": quadruples
    }
    filename = os.path.join(output_dir, f"{safe_filename(news['title'])}.json")
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def extract_text_from_json(folder_path="sina_news"):
    all_text = []

    for filename in os.listdir(folder_path):
        if filename.endswith(".json"):
            filepath = os.path.join(folder_path, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                quadruples = data.get("四元组", [])
                
                for quad in quadruples:
                    ent1 = quad.get("实体1", "").strip()
                    ent2 = quad.get("实体2", "").strip()
                    event = quad.get("事件", "").strip()
                    sentiment = quad.get("情感", "").strip()

                    # 可按需选择使用哪些字段
                    all_text.extend([ent1, ent2, event, sentiment])

    # 拼接为一个空格分隔的长字符串，作为词云输入
    return ' '.join([t for t in all_text if t])  # 过滤空字符串

def get_all_news(keyword):
    fenghuang = get_fenghuang_news(keyword)
    sina = get_sina_news(keyword)
    baidu = get_baidu_news_with_selenium(keyword)
    return fenghuang + sina + baidu

# 清空文件夹,避免重复抓取
def clear_folder(folder_path):
    # 检查文件夹是否存在
    if not os.path.exists(folder_path):
        print(f"路径不存在: {folder_path}")
        return

    # 遍历文件夹中的所有文件和子文件夹
    for filename in os.listdir(folder_path):
        file_path = os.path.join(folder_path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                # 删除文件或符号链接
                os.remove(file_path)
            elif os.path.isdir(file_path):
                # 删除文件夹及其内容
                shutil.rmtree(file_path)
        except Exception as e:
            print(f'删除 {file_path} 时出错: {e}')
            
def process_in_one(keyword):
    
    shantou_city=['龙湖区','金平区','濠江区','潮阳区','潮南区','澄海区','南澳县']
    if keyword in shantou_city:
        json_file =  os.path.join('shantou_city', keyword)
        
    else: 
        json_file =os.path.join('shantou_city', keyword)

    # 获取所有新闻
    news = get_all_news(keyword)
    
    #清空已有文件夹,后续可能要优化逻辑
    clear_folder(json_file)
    
    for i, news in enumerate(news[:30]):
        print(f"\n🔄 正在处理第 {i+1} 条新闻：《{news['title']}》")

        # 摘要
        get_sum= summarize_news(news['body'])
        summary, type = get_sum[0], get_sum[1]
        
        print(f"摘要：{summary}")
        print("✅ 摘要完成")

        # 提取四元组
        triplet_text = extract_quadruples(news['body'])
        if not triplet_text:
            print("⚠️ 四元组提取失败")
            continue
        grouped_triplets = parse_quadruples(triplet_text)
        print("✅ 四元组提取完成")
        
        # 保存
        save_news_json_with_quadruples(news, summary,type, grouped_triplets,json_file)
        print(f"✅ 已保存为 JSON 文件")
    
    return f"{keyword} 抓取并处理了{len(news)} 条新闻。"
    
if __name__ == "__main__":
    keyword = "汕头"
    process_in_one(keyword)