import time
import json
import random
from playwright.sync_api import sync_playwright

def human_scroll(page, times=5):
    for _ in range(times):
        page.mouse.wheel(0, random.randint(800, 1500))
        time.sleep(random.uniform(1.0, 2.0))

def extract_search_results(page, keyword):
    """
    提取搜索结果，分为标题包含关键词和不包含关键词的两类
    返回两个列表：questions_list和related_list
    """
    questions_list = []
    related_list = []
    cards = page.query_selector_all('div[data-za-detail-view-path-module="SearchResultList"] > div')
    for card in cards:
        anchors = card.query_selector_all('a')
        for a in anchors:
            href = a.get_attribute('href')
            if href and href.startswith('/question/'):
                title = a.inner_text().strip()
                full_url = f"https://www.zhihu.com{href}"
                if keyword in title:
                    questions_list.append((title, full_url))
                else:
                    print(f"⛔ 相关问题（标题无关键词）：{title}")
                    related_list.append({"title": title, "url": full_url})
    # 去重并返回
    questions_unique = list({t: u for t, u in questions_list}.items())
    # related_list不用去重了，通常不会重复
    return questions_unique, related_list

def extract_answers_with_comments(page, max_answers=3, max_comments=3):
    answer_blocks = page.query_selector_all('div.List-item')
    results = []

    for ans in answer_blocks[:max_answers]:
        content_div = ans.query_selector('div.RichContent-inner')
        time_tag = ans.query_selector('div.ContentItem-time > a > span')

        if not content_div:
            continue

        answer_text = content_div.inner_text().strip()[:500]
        answer_time = time_tag.inner_text().strip() if time_tag else "unknown"

        # 点击“查看全部评论”按钮
        try:
            show_all_button = ans.query_selector('button.ContentItem-action')
            if show_all_button and "评论" in show_all_button.inner_text():
                show_all_button.click()
                time.sleep(2)
        except Exception as e:
            print("评论展开失败：", e)

        comments = []
        try:
            comment_container = ans.query_selector('div.Comments-container.css-plbgu')
            if comment_container:
                content_nodes = comment_container.query_selector_all('div.CommentContent.css-1jpzztt')
                time_nodes = comment_container.query_selector_all('span.css-12cl38p')  # 注意这里类名拼写正确

                for i in range(min(len(content_nodes), len(time_nodes), max_comments)):
                    try:
                        p_tag = content_nodes[i].query_selector('p')
                        comment_text = p_tag.inner_text().strip() if p_tag else ""
                        comment_time = time_nodes[i].inner_text().strip()

                        if comment_text:
                            comments.append({
                                "comment": comment_text,
                                "time": comment_time
                            })
                    except Exception as e:
                        print("⛔ 单条评论提取异常：", e)
            else:
                print("⚠️ 无评论容器 Comments-container")
        except Exception as e:
            print("⛔ 评论抓取失败：", e)

        results.append({
            "answer": answer_text,
            "time": answer_time,
            "comments": comments
        })

    return results

def zhihu_scraper_to_json(keyword,output_file, max_questions=3, max_answers=3, max_comments=3):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False,
                                    args=["--disable-blink-features=AutomationControlled"])
        context = browser.new_context(storage_state="playwright_auth/storage.json",
                                      user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                                 "AppleWebKit/537.36 (KHTML, like Gecko) "
                                                 "Chrome/114.0.0.0 Safari/537.36")

        page = context.new_page()
        print(f"搜索关键词：{keyword}")
        page.goto(f"https://www.zhihu.com/search?q={keyword}")
        human_scroll(page, times=5)

        questions_list, related_list = extract_search_results(page, keyword)
        print(f"共找到 {len(questions_list)} 个符合关键词的问题，准备抓取前 {max_questions} 个。")
        print(f"共找到 {len(related_list)} 个相关问题（标题无关键词）。")

        data = {
            "questions": {},
            "related": related_list
        }

        for i, (title, url) in enumerate(questions_list[:max_questions]):
            print(f"\n📌 正在抓取问题 {i+1}：{title}")
            qpage = context.new_page()
            qpage.goto(url)
            time.sleep(random.uniform(1.0, 2.0))
            human_scroll(qpage, times=5)

            qa_list = extract_answers_with_comments(qpage, max_answers=max_answers, max_comments=max_comments)
            data["questions"][title] = {
                "url": url,
                "answers": qa_list
            }
            qpage.close()

        filename = output_file
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 抓取完成，结果已保存至 {filename}")

        browser.close()

if __name__ == "__main__":
    zhihu_scraper_to_json("汕头","big汕头.json", max_questions=2, max_answers=10, max_comments=30)
