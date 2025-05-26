from flask import Flask, request, jsonify, render_template
import json
from crawler import *
from draw_pyvis import generate_quadruple_graph_html_with_link
from my_wordcloud import  wordcloud_process
import os
from io import BytesIO
from flask import send_file
import base64
from flask import Response, stream_with_context
import sys
import threading
import time
from zhihu_web import zhihu_scraper_to_json
from pie_web import collect_statistics_from_folder, plot_pie_chart
from doc_web import generate_report_to_bytes,generate_report


app = Flask(__name__)
app.config['news_keyword'] = '汕头'
app.config['comment_keyword'] = '汕头'
keyword_lock = threading.Lock()

@app.route("/")
def index():
    with open("news_data.json", "r", encoding="utf-8") as f:
        news_list = json.load(f)
        
    folders=['../baidu_news','../sina_news','../fenghuang_news']
    #draw_quadruple_graph_from_folders(folders)
    
    return render_template("index.html", news=news_list)

#已经弃用，改用了sse
@app.route('/crawl', methods=['POST'])
def crawl():
    data = request.get_json()
    region = data.get('region')

    if not region:
        return jsonify({"message": "未提供区域名称"}), 400

    try:
        result_msg = process_in_one(region)
        return jsonify({"message": result_msg}), 200
    except Exception as e:
        print("❌ 出错：", e)
        return jsonify({"message": f"处理失败：{str(e)}"}), 500

@app.route('/crawl_sse')
def crawl_sse():
    def generate():
        print("[DEBUG] 当前关键词为：", get_keywords())
        try:
            with keyword_lock:
                keyword = app.config['news_keyword']
                region = keyword

            if not keyword:
                yield f"data: {json.dumps({'message': '❌ 当前关键词为空，请先点击地图设置'})}\n\n"
                return

            yield f"data: {json.dumps({'message': f'🌍 开始抓取 {region} 的新闻...'})}\n\n"
            sys.stdout.flush()
            time.sleep(0.1)

            shantou_city = ['龙湖区','金平区','濠江区','潮阳区','潮南区','澄海区','南澳县','汕头']
            json_file = f'shantou_city/{region}' if region in shantou_city else f'json_file/{region}'
            os.makedirs(json_file, exist_ok=True)
            clear_folder(json_file)

            news_list = get_all_news(region)
            total = min(30, len(news_list))

            print('进入循环')
            for i, news in enumerate(news_list[:30]):
                title = news['title']
                yield f"data: {json.dumps({'message': f'🔄 正在处理第 {i+1}/{total} 条：《{title}》'})}\n\n"
                sys.stdout.flush()
                time.sleep(0.1)

                summary,news_type = summarize_news(news['body'])
                
                sys.stdout.flush()
                time.sleep(0.1)
                triplet_text = extract_quadruples(news['body'])
                if not triplet_text:
                    print("⚠️ 四元组提取失败")
                    continue
                
                sys.stdout.flush()
                time.sleep(0.1)
                grouped_triplets = parse_quadruples(triplet_text)
                
                sys.stdout.flush()
                time.sleep(0.1)
                save_news_json_with_quadruples(news, summary,news_type, grouped_triplets, json_file)

                yield f"data: {json.dumps({'message': f'✅ 已完成《{title}》'})}\n\n"
                sys.stdout.flush()
                time.sleep(0.1)

            yield f"data: {json.dumps({'message': f'✅ 所有新闻处理完成，共 {total} 条。'})}\n\n"
            sys.stdout.flush()
        except Exception as e:
            yield f"data: {json.dumps({'message': f'❌ 出错：{str(e)}'})}\n\n"
            sys.stdout.flush()

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

#这个函数用来抓取知乎数据
@app.route('/crawl_zhihu', methods=['POST'])
def crawl_zhihu():
    keyword = app.config.get('comment_keyword', '').strip()
    if not keyword:
        return jsonify({'message': '未配置关键词'}), 400
    print(f"当前知乎关键词：{keyword}")

    try:
        
        filename = f"{keyword}.json"
        output_path = os.path.join("zhihu_json_file", filename)
        os.makedirs("zhihu_data", exist_ok=True)

        zhihu_scraper_to_json(keyword=keyword, output_file=output_path)

        return jsonify({'message': f'知乎数据抓取成功，已保存为 {filename}'})
    except Exception as e:
        return jsonify({'message': f'抓取失败：{str(e)}'}), 500

#这个函数用来生成实体网络图
@app.route("/get_graph_html")
def get_graph_html():
    keyword =  get_keywords()
    city_keyword = keyword['news_keyword']

    folder_paths =  [os.path.join('shantou_city', city_keyword)]
    

    graph_html = generate_quadruple_graph_html_with_link(folder_paths)
    
    # 临时写入文件测试
    # with open("debug_graph.html", "w", encoding="utf-8") as f:
    #     f.write(graph_html)
        
    return graph_html

@app.route('/wordcloud', methods=['POST'])
def wordcloud_page():
    # 从系统配置中读取当前关键词
    keyword = app.config['news_keyword']
    folder_path = os.path.join("shantou_city", keyword)
    
    print(f"词云.当前关键词：{keyword}")
    print(f"词云.当前路径：{folder_path}")

    if not os.path.isdir(folder_path):
        return {"status": "fail", "message": f"无效的路径：{folder_path}"}

    # 调用词云生成函数
    image = wordcloud_process(folder_path)

    # 图片转 base64
    buffered = BytesIO()
    image.save(buffered, format="PNG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {"status": "success", "img_data": img_base64}

#用于获取当前的关键词
@app.route('/status')
def get_status():
    return jsonify({
        "news_keyword": app.config['news_keyword'],
        "comment_keyword": app.config['comment_keyword']
    })

#用于设置关键词，但只有城市关键词
@app.route('/set_keyword', methods=['POST'])
def set_keyword():
    data = request.get_json()
    region = data.get("keyword")
    
    print(f"收到的关键词：{region}")
    
    if region:
        with keyword_lock:
            app.config['news_keyword'] = region
        print(f"✅ 已设置关键词为：{region}")
        return {"status": "success", "message": f"关键词已设为：{region}"}
    else:
        return {"status": "fail", "message": "未提供region"}

#用于设置关键词
@app.route('/set_keywords', methods=['POST'])
def set_keywords():
    data = request.get_json()
    news = data.get('news_keyword')
    comment = data.get('news_keyword')

    with keyword_lock:
        if news:
            app.config['news_keyword'] = news
        if comment:
            app.config['comment_keyword'] = comment
    
    print(f"✅ 已设置关键词为：{news}，{comment}")

    return jsonify({"message": "✅ 关键词设置成功！"})

#用于设置关键词，但不是前后端交互
def set_keywords_just_py(news=None, comment=None):
    with keyword_lock:
        if news: app.config['news_keyword'] = news
        if comment: app.config['comment_keyword'] = comment

#用于获取当前的关键词
def get_keywords():
    with keyword_lock:
        return {
            "news_keyword": app.config['news_keyword'],
            "comment_keyword": app.config['comment_keyword']
        }

#用于绘制饼图
@app.route("/update_piecharts", methods=["POST"])
def update_piecharts():
    keyword = app.config['news_keyword']
    folder_path = os.path.join("shantou_city", keyword)
    
    emotion_counts, type_counts = collect_statistics_from_folder(folder_path)
    emotion_img = plot_pie_chart(emotion_counts, keyword+"新闻类型分布")
    type_img = plot_pie_chart(type_counts, keyword+"新闻类型分布")
    return {
        "status": "success",
        "emotion_img": emotion_img,
        "type_img": type_img
    }

#用于生成报告
@app.route("/generate_report", methods=["GET"])
def download_report():
    news_keyword = app.config['news_keyword']
    print(f"当前关键词：{news_keyword}")
    doc_bytes = generate_report_to_bytes(news_keyword)
    return send_file(
        doc_bytes,
        mimetype="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        download_name="城市舆情分析报告.docx",
        as_attachment=True
    )
    
    
if __name__ == "__main__":
    app.run(debug=True)
